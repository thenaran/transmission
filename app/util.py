#
# Copyright 2012 Narantech Inc.

# This program is a property of Narantech Inc. Any form of infringement is
# strictly prohibited. You may not, but not limited to, copy, steal, modify # and/or redistribute without appropriate permissions under any circumstance.
#
#  __    _ _______ ______   _______ __    _ _______ _______ _______ __   __
# |  |  | |   _   |    _ | |   _   |  |  | |       |       |       |  | |  |
# |   |_| |  |_|  |   | || |  |_|  |   |_| |_     _|    ___|       |  |_|  |
# |       |       |   |_||_|       |       | |   | |   |___|       |       |
# |  _    |       |    __  |       |  _    | |   | |    ___|      _|       |
# | | |   |   _   |   |  | |   _   | | |   | |   | |   |___|     |_|   _   |
# |_|  |__|__| |__|___|  |_|__| |__|_|  |__| |___| |_______|_______|__| |__|


"""The utility module.
"""


import logging
import json
import os
from cStringIO import StringIO


class Settings(object):
  """Abstraction for configuration setting values.
  """
  def __init__(self, paths):
    """
    Args:
      paths: a iterator of config file path
    """
    self._paths = paths
    self._modified = False
    self.reload()

  def _read(self, paths):
    self._config = {}
    self._config_symbol = {}
    self._merged_config = {}
    self._custom_config = {}
    self._custom_config_symbol = {}

    for path in paths:
      if os.path.exists(path):
        with open(path, 'r') as rf:
          config_data = rf.read()
          try:
            self._update_value(json.loads(config_data))
          except:
            logging.exception("Occured error while loading a config.:\n"
                              "path: %s\ncontents:\n%s", path, config_data)

  def _update_value(self, config):
    #TODO: Needs to optimize handling config custom values

    values = [('', k, v) for k, v in config.items()]
    noneed_keys = set()

    while values:
      parent_key, key, value = values.pop()
      key_io = StringIO()
      key_io.write(parent_key)
      key_io.write(key)
      if isinstance(value, dict):
        key_io.write('.')
        for k, v in value.items():
          values.append((key_io.getvalue(), k, v))
      else:
        if not self._config:
          self._config_symbol[key_io.getvalue()] = value
        elif key_io.getvalue() in self._config_symbol and value:
          self._custom_config_symbol[key_io.getvalue()] = value
        else:
          noneed_keys.add(key_io.getvalue())
        key_io.close()

    for k in noneed_keys:
      keys = self._parse_key(key)
      sub_config = config
      for key in keys[:-1]:
        sub_config = sub_config[key]
      del sub_config[keys[-1]]

    if not self._config:
      self._config = config
      self._merged_config = config.copy()
    else:
      self._custom_config = config
      self._merged_config = self._merge(self._merged_config, config)

  def _merge(self, src, trg, keys=[]):
    for key in trg:
      trg_value = trg[key]
      src_value = src.get(key)
      if isinstance(src_value, dict) and isinstance(trg_value, dict):
        self._merge(src_value, trg_value, keys + [str(key)])
      else:
        src[key] = trg_value
    return src

  def _parse_key(self, key):
    """ Parsing a string key to a list sorted by hirerchy.
    """
    return key.split('.')

  def _check_need_merge(self):
    if not self._modified:
      return
    for key, value in self._custom_config_symbol.items():
      keys = self._parse_key(key)
      config = self._custom_config
      level = 0
      for k in keys:
        level += 1
        v = config.get(k)
        if isinstance(v, dict):
          config = v
          continue
        break
      last_key = keys[-1]
      sub_keys = keys[level - 1:]
      default_value = self._config_symbol.get(key)
      if value == default_value:
        if level == len(keys):
          del config[last_key]
        else:
          merged_config = self._merged_config
          for k in sub_keys[:-1]:
            merged_config = merged_config.get(k)
          merged_config[last_key] = default_value
      else:
        if level == len(keys):
          config[last_key] = value
        else:
          new_value = value
          while sub_keys:
            new_value = {sub_keys.pop(): new_value}
          config.update(new_value)
    self._merged_config = self._merge(self._merged_config,
                                      self._custom_config)
    self._modified = False

  def to_string(self):
    self._check_need_merge()
    return json.dumps(self._merged_config)

  def get(self, key, default=None):
    """Gets the string value associated with the key.
    """
    value = self._custom_config_symbol.get(key)
    if value:
      return value
    value = self._config_symbol.get(key)
    if value:
      return value
    self.set(key, default)
    return default

  def get_int(self, key, default=0):
    """Gets the integer value associated with the key.
    """
    return int(self.get(key, default))

  def get_float(self, key, default=0):
    """Gets the float value accociated with the key.
    """
    return float(self.get(key, default))

  def get_bool(self, key, default=False):
    """Gets the boolean value accociated with the key.
    """
    return bool(self.get(key, default))

  def set(self, key, value):
    """Sets the given value to the key.
    """
    self._modified = True
    self._custom_config_symbol[key] = value

  def __iter__(self):
    self._check_need_merge()
    return self._merged_config.__iter__()

  def reset_value(self, key):
    """Removes the customed value with specified key.
    """
    if key in self._custom_config_symbol:
      self._modified = True
      self._custom_config_symbol[key] = self._config_symbol[key]

  def keys(self, key):
    """Returns a list of child keys available in the specified key
    """
    config = self._merged_config
    for k in self._parse_key(key):
      config = config.get(k)
      if not config:
        return []
    return config.keys()

  def get_dict(self, key=None):
    """Gets items by dictionary set
    """
    self._check_need_merge()
    config = self._merged_config
    for k in self._parse_key(key):
      config = config.get(k)
      if not config:
        return {}
    return config

  def reset(self):
    self._flush({})
    self.reload()

  def reload(self):
    """Reloads the settings from the file system.
    """
    self._read(self._paths)

  def _flush(self, config, path):
    if path:
      dst = path
    else:
      dst = self._paths
      if isinstance(self._paths, list):
        dst = self._paths[0]
    try:
      print config
      print self._config
      with open(dst, 'w') as f:
        json.dump(config, f)
    except:
      logging.exception("Failed to flush the settings.")

  def flush_newly_values(self, path=None):
    self._check_need_merge()
    self._flush(self._custom_config, path)

  def flush(self, path=None):
    """Flushes the current settings value to the given path.
    """
    self._check_need_merge()
    self._flush(self._merged_config, path)
