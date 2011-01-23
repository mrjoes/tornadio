# -*- coding: utf-8 -*-
"""
    tornadio.polling
    ~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time
import logging
import json

from tornado import ioloop
from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import session, pollingsession

class TornadioPollingHandlerBase(RequestHandler):
    """All polling transport implementations derive from this class.

    Polling transports have following things in common:

    1. They use GET to read data from the server
    2. They use POST to send data to the server
    3. They use sessions - first message sent back from the server is session_id
    4. Session is used to create one virtual connection for one or more HTTP
    connections
    5. If GET request is not running, data will be cached on server side. On
    next GET request, all cached data will be sent to the client in one batch
    6. If there were no GET requests for more than 15 seconds (default), virtual
    connection will be closed - session entry will expire
    """
    _sessions = session.SessionContainer()

    # TODO: Configurable callback timeout
    _session_cleanup = ioloop.PeriodicCallback(_sessions.expire, 15000).start()

    io_loop = ioloop.IOLoop.instance()

    def __init__(self, handler, session_id):
        """Default constructor.

        Accepts handler and session_id (if available) and handles request.
        """
        self.handler = handler

        # Decide what to do with the session - either create new or
        # get one from the cache.
        if not session_id:
            self.session = self._create_session(handler.connection)
        else:
            self.session = self._get_session(session_id)

            if self.session is None or self.session.is_closed:
                # TODO: Send back disconnect message?
                raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self).__init__(handler.application,
                                                         handler.request)

    @classmethod
    def _create_session(cls, connection):
        return cls._sessions.create(pollingsession.PollingSession,
                                    expiry=15,
                                    connection=connection)

    @classmethod
    def _get_session(cls, session_id):
        return cls._sessions.get(session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        """Default GET handler."""
        raise NotImplemented()

    @asynchronous
    def post(self, *args, **kwargs):
        """Default POST handler."""
        raise NotImplemented()

    def data_available(self, data_available):
        """Called by the session when some data is available"""
        raise NotImplemented()

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

    @asynchronous
    def preflight(self):
        """Handles request authentication"""
        if self.request.headers.has_key('Origin'):
            if self.verify_origin():
                self.set_header('Access-Control-Allow-Origin',
                                self.request.headers['Origin'])

                if self.request.headers.has_key('Cookie'):
                    self.set_header('Access-Control-Allow-Credentials', True)

                return True
            else:
                return False
        else:
            return True

    def verify_origin(self):
        # TODO: Verify origin
        return True

class TornadioXHRPollingSocketHandler(TornadioPollingHandlerBase):
    """XHR polling transport implementation.

    Polling mechanism uses long-polling AJAX GET to read data from the server
    and POST to send data to the server.

    Properties of the XHR polling transport:

    1. If there was no data for more than 20 seconds (by default) from the
    server, GET connection will be closed to avoid HTTP timeouts. In this case
    socket.io client-side will just make another GET request.
    2. When new data is available on server-side, it will be sent through the
    open GET connection or cached otherwise.
    """

    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # Avoid double connections
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        # TODO: Configurable timeout
        # TODO: Do not setup timeout if there was something in the output queue
        self._timeout = self.io_loop.add_timeout(time.time() + 20,
                                                 self._polling_timeout)

        self.session.flush()

    def _polling_timeout(self):
        if self.session:
            self.session.send('')

    @asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')

        data = self.get_argument('data')

        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        # TODO: async
        self.session.raw_message(data.decode('utf-8', 'replace'))

        self.write('ok')
        self.finish()

    def _detach(self):
        self.session.remove_handler(self)
        self.session = None

    def on_connection_close(self):
        self._detach()

    # TODO: Async
    def data_available(self, worker):
        # Encode message
        message = self.session.dump_messages()

        self.preflight()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Detach connection
        self._detach()

class TornadioXHRMultipartSocketHandler(TornadioPollingHandlerBase):
    """XHR Multipart transport implementation.

    Transport properties:
    1. One persistent GET connection used to receive data from the server
    2. Sends heartbeat messages to keep connection alive each 12 seconds
    (by default)
    """
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary="socketio"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        self.session.reset_heartbeat()

    @asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')

        data = self.get_argument('data')

        if not self.preflight():
            print 'Unauthorized'
            raise HTTPError(401, 'unauthorized')

        # TODO: async
        self.session.raw_message(data.decode('utf-8', 'replace'))

        self.write('ok')
        self.finish()

    def on_connection_close(self):
        self.session.stop_heartbeat()
        self.session.remove_handler(self)

    # TODO: Async
    def data_available(self, worker):
        # Encode message
        message = self.session.dump_messages()

        self.preflight()
        self.write("Content-Type: text/plain; charset=us-ascii\n\n")
        self.write(message + '\n')
        self.write('--socketio\n')
        self.flush()

        self.session.delay_heartbeat()

class TornadioHtmlFileSocketHandler(TornadioPollingHandlerBase):
    """IE HtmlFile protocol implementation.

    Uses hidden frame to stream data from the server in one connection.

    Unfortunately, it is unknown if this transport works, as socket.io
    client-side fails in IE7/8.
    """
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        self.set_header('Content-Type', 'text/html')
        self.set_header('Connection', 'keep-alive')
        self.set_header('Transfer-Encoding', 'chunked')
        self.write('<html><body>%s' % (' ' * 244))

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        self.session.reset_heartbeat()

    @asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')

        data = self.get_argument('data')

        if not self.preflight():
            print 'Unauthorized'
            raise HTTPError(401, 'unauthorized')

        # TODO: async
        self.session.raw_message(data.decode('utf-8', 'replace'))

        self.write('ok')
        self.finish()

    def on_connection_close(self):
        self.session.stop_heartbeat()
        self.session.remove_handler(self)

    # TODO: Async
    def data_available(self, worker):
        # Encode message
        message = self.session.dump_messages()

        self.write(
            '<script>parent.s_(%s), document);</script>' % json.dumps(message)
            )
        self.flush()

        self.session.delay_heartbeat()

class TornadioJSONPSocketHandler(TornadioXHRPollingSocketHandler):
    """JSONP protocol implementation.
    """
    @asynchronous
    def get(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).get(*args, **kwargs)

    @asynchronous
    def post(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).post(*args, **kwargs)

    # TODO: Async
    def data_available(self, worker):
        message = 'io.JSONP[%s]._(%s);' % (
            self._index,
            json.dumps(self.session.dump_messages())
            )

        self.preflight()
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Detach connection
        self._detach()
