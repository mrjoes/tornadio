# -*- coding: utf-8 -*-
"""
    tornadio.polling
    ~~~~~~~~~~~~~~~~

    This module implements socket.io polling transports.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time
try:
    import simplejson as json
except ImportError:
    import json

from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import pollingsession

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
    def __init__(self, router, session_id):
        """Default constructor.

        Accepts router instance and session_id (if available) and handles
        request.
        """
        self.router = router
        self.session_id = session_id
        self.session = None

        super(TornadioPollingHandlerBase, self).__init__(router.application,
                                                         router.request)

    def _execute(self, transforms, *args, **kwargs):
        # Initialize session either by creating new one or
        # getting it from container
        if not self.session_id:
            session_expiry = self.router.settings['session_expiry']

            self.session = self.router.sessions.create(
                pollingsession.PollingSession,
                session_expiry,
                router=self.router,
                args=args,
                kwargs=kwargs)
        else:
            self.session = self.router.sessions.get(self.session_id)

            if self.session is None or self.session.is_closed:
                # TODO: Send back disconnect message?
                raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self)._execute(transforms,
                                                         *args, **kwargs)

    @asynchronous
    def get(self, *args, **kwargs):
        """Default GET handler."""
        raise NotImplementedError()

    @asynchronous
    def post(self, *args, **kwargs):
        """Default POST handler."""
        raise NotImplementedError()

    def data_available(self, raw_data):
        """Called by the session when some data is available"""
        raise NotImplementedError()

    @asynchronous
    def options(self, *args, **kwargs):
        """XHR cross-domain OPTIONS handler"""
        self.preflight()
        self.finish()

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
        """Verify if request can be served"""
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
    def __init__(self, router, session_id):
        self._timeout = None

        self._timeout_interval = router.settings['xhr_polling_timeout']

        super(TornadioXHRPollingSocketHandler, self).__init__(router,
                                                              session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            # Check to avoid double connections
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        if not self.session.send_queue:
            self._timeout = self.router.io_loop.add_timeout(
                time.time() + self._timeout_interval,
                self._polling_timeout)
        else:
            self.session.flush()

    def _polling_timeout(self):
        # TODO: Fix me
        if self.session:
            self.data_available('')

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.get_argument('data')
        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain')
        self.write('ok')
        self.finish()

    def _detach(self):
        if self.session:
            self.session.remove_handler(self)
            self.session = None

    def on_connection_close(self):
        self._detach()

    def data_available(self, raw_data):
        self.preflight()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(raw_data))
        self.write(raw_data)
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

        self.set_header('Content-Type',
                        'multipart/x-mixed-replace;boundary="socketio"')
        self.set_header('Connection', 'keep-alive')
        self.write('--socketio\n')

        # Dump any queued messages
        self.session.flush()

        # We need heartbeats
        self.session.reset_heartbeat()

    @asynchronous
    def post(self, *args, **kwargs):
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.get_argument('data')
        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain')
        self.write('ok')
        self.finish()

    def on_connection_close(self):
        if self.session:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def data_available(self, raw_data):
        self.preflight()
        self.write("Content-Type: text/plain; charset=us-ascii\n\n")
        self.write(raw_data + '\n')
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
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        data = self.get_argument('data')
        self.async_callback(self.session.raw_message)(data)

        self.set_header('Content-Type', 'text/plain')
        self.write('ok')
        self.finish()

    def on_connection_close(self):
        if self.session:
            self.session.stop_heartbeat()
            self.session.remove_handler(self)

    def data_available(self, raw_data):
        self.write(
            '<script>parent.s_(%s),document);</script>' % json.dumps(raw_data)
            )
        self.flush()

        self.session.delay_heartbeat()

class TornadioJSONPSocketHandler(TornadioXHRPollingSocketHandler):
    """JSONP protocol implementation.
    """
    def __init__(self, router, session_id):
        self._index = None

        super(TornadioJSONPSocketHandler, self).__init__(router, session_id)

    @asynchronous
    def get(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).get(*args, **kwargs)

    @asynchronous
    def post(self, *args, **kwargs):
        self._index = kwargs.get('jsonp_index', None)
        super(TornadioJSONPSocketHandler, self).post(*args, **kwargs)

    def data_available(self, raw_data):
        message = 'io.JSONP[%s]._(%s);' % (
            self._index,
            json.dumps(raw_data)
            )

        self.preflight()
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Detach connection
        self._detach()
