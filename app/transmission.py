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
from clique import Lazy

# 3rd party
import transmissionrpc


__DATA__ = Lazy()
__DATA__.torrent = None

class Torrent(object):
  """
  https://bitbucket.org/blueluna/transmissionrpc/src
  torrent object status new
  0 : stopped
  1 : check pending
  2 : checking
  3 : download pending
  4 : downloading
  5 : seed pending
  6 : seeding
  """
  def __init__(self, torrent):
    self._torrent = torrent
    self.t_id = torrent.id
    self.name = torrent.name.encode('utf-8')
    self.status = torrent.status
    self.download_dir = torrent.downloadDir.encode('utf-8')
    self.progress = torrent.progress

  def update(self):
    self._torrent.update()

  def start(self):
    self._torrent.start()

  def stop(self):
    self._torrent.stop()


def _connect_torrent_client():
  if not __DATA__.torrent:
    torrent = transmissionrpc.Client('127.0.0.1', port=9091)
    __DATA__.torrent = torrent


def get_list():
  torrent_list = []
  try:
    """
    torrent = transmissionrpc.Client('127.0.0.1', port=9091,
                                     user="transmission",
                                     password="transmission")
    """
    _connect_torrent_client()

    for torrent in __DATA__.torrent.get_torrents():
      torrent_list.append(Torrent(torrent))
  except:
    logging.warn("Failed get torrent list.", exc_info=True)

  return torrent_list


def get_torrent_client():
  _connect_torrent_client()
  return __DATA__.torrent


def add_torrent(torrent):
  """ torrent - uri to a torrent or base64 encoded torrent data.
  """
  _connect_torrent_client()
  __DATA__.torrent.add_torrent(torrent)


def start_torrent(ids):
  _connect_torrent_client()
  __DATA__.torrent.start_torrent(ids)


def stop_torrent(ids):
  _connect_torrent_client()
  __DATA__.torrent.stop_torrent(ids)
