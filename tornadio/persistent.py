# -*- coding: utf-8 -*-
"""
    tornadio.persistent
    ~~~~~~~~~~~~~~~~~~~

    Persistent transport implementations.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

import tornado
from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    """WebSocket handler.
    """
    def __init__(self, router, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.router = router

        super(TornadioWebSocketHandler, self).__init__(router.application,
                                                       router.request)

    # HAProxy websocket fix.
    # Merged from:
    # https://github.com/facebook/tornado/commit/86bd681ff841f272c5205f24cd2a613535ed2e00
    def _execute(self, transforms, *args, **kwargs):
        # Next Tornado will have the built-in support for HAProxy
        if tornado.version_info < (1, 2, 0):
            # Write the initial headers before attempting to read the challenge.
            # This is necessary when using proxies (such as HAProxy),
            # need to see the Upgrade headers before passing through the
            # non-HTTP traffic that follows.
            self.stream.write(
                "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
                "Upgrade: WebSocket\r\n"
                "Connection: Upgrade\r\n"
                "Server: TornadoServer/%(version)s\r\n"
                "Sec-WebSocket-Origin: %(origin)s\r\n"
                "Sec-WebSocket-Location: ws://%(host)s%(path)s\r\n\r\n" % (dict(
                        version=tornado.version,
                        origin=self.request.headers["Origin"],
                        host=self.request.host,
                        path=self.request.path)))

        super(TornadioWebSocketHandler, self)._execute(transforms, *args,
                                                       **kwargs)


    def _write_response(self, challenge):
        if tornado.version_info < (1, 2, 0):
            self.stream.write("%s" % challenge)
            self.async_callback(self.open)(*self.open_args, **self.open_kwargs)
            self._receive_message()
        else:
            super(TornadioWebSocketHandler, self)._write_response(challenge)

    def open(self, *args, **kwargs):
        # Create connection instance
        heartbeat_interval = self.router.settings['heartbeat_interval']
        self.connection = self.router.connection(self,
                                                 self.router.io_loop,
                                                 heartbeat_interval)

        # Initialize heartbeats
        self.connection.reset_heartbeat()

        # Fix me: websocket is dropping connection if we don't send first
        # message
        self.send('no_session')

        self.connection.on_open(*args, **kwargs)

    def on_message(self, message):
        self.async_callback(self.connection.raw_message)(message)

    def on_close(self):
        try:
            self.connection.on_close()
        finally:
            self.connection.is_closed = True
            self.connection.stop_heartbeat()

    def send(self, message):
        self.write_message(proto.encode(message))
        self.connection.delay_heartbeat()

class TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, router, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(router, session_id)
