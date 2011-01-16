import time
import logging
import json

from tornado import ioloop
from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import session, pollingsession

class TornadioPollingHandlerBase(RequestHandler):
    _sessions = session.SessionContainer()

    # TODO: Configurable callback timeout
    _session_cleanup = ioloop.PeriodicCallback(_sessions.expire, 30000).start()

    io_loop = ioloop.IOLoop.instance()

    def __init__(self, handler, session_id):
        self.handler = handler

        print 'Polling: %s' % session_id

        if not session_id:
            self.session = self._create_session(handler.connection)
        else:
            self.session = self._get_session(session_id)

            if self.session is None:
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
        raise NotImplemented()

    @asynchronous
    def post(self, *args, **kwargs):
        raise NotImplemented()

    def data_available(self, data_available):
        "Called by the session when some data is available"
        raise NotImplemented()

    @asynchronous
    def options(self, *args, **kwargs):
        logging.debug('OPTIONS')
        self.preflight()
        self.finish()

    @asynchronous
    def preflight(self):
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
    @asynchronous
    def get(self, *args, **kwargs):
        print 'GET %s, %s' % (args, kwargs)

        if not self.session.set_handler(self):
            print 'Failed to set handler'
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        # TODO: Configurable timeout
        # TODO: Do not setup timeout if there was something in the queue
        self._timeout = self.io_loop.add_timeout(time.time() + 5,
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
            print 'Unauthorized'
            raise HTTPError(401, 'unauthorized')

        # TODO: async
        self.session.raw_message(data.decode('utf-8', 'replace'))

        self.write('ok')
        self.finish()

    def _detach(self):
        self.session.remove_handler(self)
        self.session = None

    def on_connection_close(self):
        print 'Connection closed'
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
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            print 'Failed to set handler'
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        print 'Multipart GET'

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

        # TODO: If we're still connected - reset heartbeat
        #if self.request.connection.stream.socket:
        #    self.session.reset_heartbeat()

class TornadioXHRHtmlFileSocketHandler(TornadioPollingHandlerBase):
    @asynchronous
    def get(self, *args, **kwargs):
        if not self.session.set_handler(self):
            print 'Failed to set handler'
            # TODO: Error logging
            raise HTTPError(401, 'Forbidden')

        print 'HTML FILE'

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

        # TODO: If we're still connected - reset heartbeat
        #if self.request.connection.stream.socket:
        #    self.session.reset_heartbeat()
