# -*- coding: utf-8 -*-
"""
    tornadio.persistent
    ~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    """WebSocket handler.
    """
    def __init__(self, handler, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.handler = handler

        # Create connection instance
        heartbeat_interval = handler.settings['heartbeat_interval']
        self.connection = handler.connection(self, heartbeat_interval)

        super(TornadioWebSocketHandler, self).__init__(handler.application,
                                                       handler.request)

    def open(self, *args, **kwargs):
        self.connection.reset_heartbeat()

        # Fix me: websocket is dropping connection if we don't send first
        # message
        self.send('no_session')

        self.connection.on_open(*args, **kwargs)

    def on_message(self, message):
        self.async_callback(self.connection.raw_message)(message)

    def on_close(self):
        self.connection.on_close()
        self.connection.is_closed = True

        self.connection.stop_heartbeat()

    def send(self, message):
        self.write_message(proto.encode(message))
        self.connection.delay_heartbeat()

class TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, handler, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(handler, session_id)
