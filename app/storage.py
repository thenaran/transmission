# -*- coding: utf-8 -*-
# Copyright 2012-2014 Narantech Inc. All rights reserved.
#  __    _ _______ ______   _______ __    _ _______ _______ _______ __   __
# |  |  | |   _   |    _ | |   _   |  |  | |       |       |       |  | |  |
# |   |_| |  |_|  |   | || |  |_|  |   |_| |_     _|    ___|       |  |_|  |
# |       |       |   |_||_|       |       | |   | |   |___|       |       |
# |  _    |       |    __  |       |  _    | |   | |    ___|      _|       |
# | | |   |   _   |   |  | |   _   | | |   | |   | |   |___|     |_|   _   |
# |_|  |__|__| |__|___|  |_|__| |__|_|  |__| |___| |_______|_______|__| |__|

# default
import logging

# clique
import clique.isc
import clique.runtime
from clique import Lazy
from clique.isc import Endpoints

# transmission
import main


__DATA__ = Lazy()
__DATA__.storage_list = []

# Name space
__MQ_NS__ = '''mq'''
__STORAGE_NS__ = '''engine.storage'''
__APP_NS__ = '''transmission'''

# Mount topic
__MOUNT_ADD_TOPIC__ = '''mount.add'''
__MOUNT_REMOVE_TOPIC__ = '''mount.remove'''

__ROOT__ = '''/'''
__MOUNT_BASE__ = '''media'''


def _event_cb(topic, msg):
  # msg is storage ident
  path = os.path.join(__ROOT__, __MOUNT_BASE__, msg)
  logging.info("Event topic : %s, msg : %s, path : %s", topic, msg, path)

  if topic == __MOUNT_ADD_TOPIC__:
    if path not in __DATA__.storage_list:
      __DATA__.storage_list.append(path)
      main.execute(path)
    logging.info("Success mount add event.")
  elif topic == __MOUNT_REMOVE_TOPIC__:
    if path in __DATA__.storage_list:
      __DATA__.storage_list.remove(path)
    logging.info("Success mount remove event.")


def _subscribe(node_id, event_ep):
  logging.info("Subscribe transmission event. node id : %s, event ep : %s",
               node_id, str(event_ep))
  if event_ep:
    ep = Endpoints(__MQ_NS__, node_id=node_id)
    ep.subscribe(__MOUNT_ADD_TOPIC__, event_ep)
    ep.subscribe(__MOUNT_REMOVE_TOPIC__, event_ep)
    logging.info("Completed mount add and remove subscribe.")
  else:
    logging.warn("Failed to subscribe transmission. Event ep is none. "
                 "Node id : %s, event ep : %s", node_id, str(event_ep))


def get_storage_list():
  return __DATA__.storage_list


def event_start():
  def rt_cb(v):
    logging.info("Event result : %s", str(v))
    if result:
      logging.info("Success register endpoint %s. Result : %s", __APP_NS__, str(v))
      node_id = result.node_id
      _subscribe(node_id, result)
    else:
      logging.warn("Failed to register endpoint.")

  return clique.isc.register_endpoint(_event_cb, __APP_NS__).then(rt_cb)


def start():
  def rt_cb(v):
    if not isinstance(v, Exception):
      __DATA__.storage_list = v
      logging.info("Storage list : %s", str(v))
      if v:
        return True
      else:
        return False
    else:
      logging.warn("Failed to get storage list. Error msg : %s", str(v))
      return False

  return Endpoints(__STORAGE_NS__).get_storage_list().then(rt_cb)
