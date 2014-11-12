#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2012-2014 Narantech Inc. All rights reserved.
#  __    _ _______ ______   _______ __    _ _______ _______ _______ __   __
# |  |  | |   _   |    _ | |   _   |  |  | |       |       |       |  | |  |
# |   |_| |  |_|  |   | || |  |_|  |   |_| |_     _|    ___|       |  |_|  |
# |       |       |   |_||_|       |       | |   | |   |___|       |       |
# |  _    |       |    __  |       |  _    | |   | |    ___|      _|       |
# | | |   |   _   |   |  | |   _   | | |   | |   | |   |___|     |_|   _   |
# |_|  |__|__| |__|___|  |_|__| |__|_|  |__| |___| |_______|_______|__| |__|


""" Main module
"""

# default
import os
import re
import logging
import subprocess

# transmission
import util
import storage
import transmission

# ambiency
import ambiency
from ambiency import sensors
from ambiency import build_sensor 
from ambiency import build_trigger 
from ambiency import build_source
from ambiency import actuators
from ambiency import build_actuator
from ambiency import build_action

# clique
import clique
import clique.web
import clique.event
import clique.runtime
from clique import Lazy
from clique.isc import find
from clique.isc import endpoint
from clique.util import Timer


__SETTINGS_PATH__ = '''/etc/transmission-daemon/settings.json'''
__DEFAULT_PATH__ = os.path.join(clique.runtime.home_dir(), "download")


__DATA__ = Lazy()
__DATA__.proc = None
__DATA__.add_initializer("config", lambda: _config())
__DATA__.completed_notify = False


def _config():
  cmd = "sudo chmod 777 {path}".format(path=__SETTINGS_PATH__)
  subprocess.check_call(cmd, shell=True)
  return util.Settings([__SETTINGS_PATH__])


@sensors
def get_sensors():
  sources = []
  sources.append(build_source('transmission', 'Transmission BT',
                              desc='Transmission BitTorrent'))
  triggers = []
  triggers.append(build_trigger('all', 'All Downloaded',
			                        	sources=sources,
			                        	desc='All torrent seed downloaded.'))
  sensors = []
  sensors.append(build_sensor('transmission',
                              'Transmission BT',
                  			      triggers,
                  			      'Transmission BitTorrent.'))
  return sensors


class Transmission(object):
  def __init__(self):
    self.run = False
    self.path = None

  def execute(self):
    try:
      subprocess.check_call('sudo /etc/init.d/transmission-daemon stop',
                            shell=True)
    except:
      pass
    finally:
      subprocess.check_call('sudo /etc/init.d/transmission-daemon start',
                            shell=True)
      self.run = True
      logging.info("Success execute transmission.", exc_info=True)


  def termiate(self):
    subprocess.check_call('sudo /etc/init.d/transmission-daemon stop',
                          shell=True)
    self.run = False
    logging.info("Success terminate transmission.")


def _checker():
  def _func():
    completed = 0
    for torrent in transmission.get_list():
      if torrent.status.lower() == "seeding":
        logging.info("%s downloaded.", torrent.name)
        cmd = "sudo chown {user}:{user} -R {path};sudo chmod -R 755 {path};"
        cmd = cmd.format(user=clique.runtime.app_name(),
                         path=os.path.join(torrent.download_dir, re.escape(torrent.name)))
        try:
          subprocess.check_call(cmd, shell=True)
          completed += 1
        except:
          logging.warn("Failed to change owner. Cmd : %s", cmd, exc_info=True)
      else:
        if int(torrent.progress) == 100:
          completed += 1

    if len(transmission.get_list()) and completed >= len(transmission.get_list()):
      logging.info("All downloaded")
      if not __DATA__.completed_notify:
        ambiency.push('transmission', 'all',
                      ['transmission'], {})
        logging.info("Fire notify ambiency")
        __DATA__.completed_notify = True
    else:
      remain_size = len(transmission.get_list()) - completed
      logging.info("Remain download size : %s", str(remain_size))
      if __DATA__.completed_notify:
        __DATA__.completed_notify = False

  Timer(clique.ioloop(), 10, _func, repeat=True)


def transmission_action(data):
  logging.debug("Transmission action data : %s", str(data))
  action = data.action_id
  if 'start_all' == action:
    for torrent in transmission.get_list():
      torrent.start()
      logging.debug("Start downloading %s file.", torrent.name)
  elif 'stop_all'  == action:
    for torrent in transmission.get_list():
      torrent.stop()
      logging.debug("Stop downloading %s file.", torrent.name)
  elif 'remove_all_list' == action:
    for torrent in transmission.get_list():
      transmission.get_torrent_client().remove_torrent(torrent.t_id)
      logging.debug("Remove %s files from list.", torrent.name)
    logging.info("Remove all torrent list. Remain size : %s",
                 str(len(transmission.get_list())))


@actuators
def get_actuators():
  sources =[]
  sources.append(build_source('transmission', 'Transmission BT',
                              desc='Transmission BitTorrent.'))
  transmission_actions = [['start_all', 'Start All', sources, [],
                           'All torrent seed start.'],
                          ['stop_all', 'Stop All', sources, [], 
                           'All torrent seed stop'],
                          ['remove_all_list', 'Remove all list', sources, [],
                           'Remove All torrent seed.']]
  actions = []
  for action in transmission_actions:
    actions.append(build_action(*action))
  actuators = []
  actuators.append(build_actuator('transmission',
                                  'Transmission BT',
                                  actions,
                                  transmission_action, 
                                  'Controll transmission.'))
  return actuators


def execute(path=None):
  if not __DATA__.proc.run:
    __DATA__.proc.execute()
    logging.info("Execute transmission process.")
  elif path and get_download_dir() == __DEFAULT_PATH__:
    if __DATA__.proc.run:
      terminate()
    set_download_dir(path)
    __DATA__.proc.execute()
    logging.info("Execute transmission process.")


def terminate():
  if __DATA__.proc.run:
    __DATA__.proc.terminate()
    logging.info("Terminate transmission process.")


def set_download_dir(path):
  if not __DATA__.proc.run:
    cmd = "sudo chmod 777 {path}".format(path=__SETTINGS_PATH__)
    subprocess.check_call(cmd, shell=True)
    __DATA__.config.set("download-dir", path)
    __DATA__.config.flush()
    logging.info("Sets the download dir path. Path : %s", path)


def get_download_dir():
  cmd = "sudo chmod 777 {path}".format(path=__SETTINGS_PATH__)
  subprocess.check_call(cmd, shell=True)
  return __DATA__.config.get("download-dir", "")


def start():
  def rt_cb(v):
    """
    v is True : storage list is exists.
    v is False : storage list is none.
    """
    logging.info("Booting transmission BT...")
    __DATA__.proc = Transmission()
    _checker()

    # Try execute before stop.
    old_path = get_download_dir()
    if v:
      path = storage.get_storage_list()[0]
      path = os.path.join("/", path.path)
      if old_path != path:
        set_download_dir(path)
        logging.info("Sets the storage path : %s", path)
      execute()
    else:
      path = __DEFAULT_PATH__
      os.path.exists(path) or os.makedirs(path)
      if old_path != path:
        set_download_dir(path)
        logging.info("Sets the default path : %s", path)
      execute()

    clique.web.set_static_path(os.path.join(clique.runtime.res_dir(), "web"))
    logging.info("Transmission BT started.")

  if not os.path.exists(__DEFAULT_PATH__):
    cmd = "sh {path} {appname}".format(path=os.path.join(clique.runtime.res_dir(), "prepare.sh"),
                                       appname=os.path.join(clique.runtime.app_name()))
    try:
      subprocess.check_call(cmd, shell=True)
    except:
      logging.warn("Failed to create %s dir.", __DEFAULT_PATH__, exc_info=True)
  else:
    cmd = "sudo chown {name}:{name} {path}".format(name=clique.runtime.app_name(), path=__DEFAULT_PATH__)
    try:
      subprocess.check_call(cmd, shell=True)
    except:
      logging.warn("Failed to create %s dir.", __DEFAULT_PATH__, exc_info=True)

  storage.event_start()
  storage.start().then(rt_cb)


if __name__ == '__main__':
  start()
