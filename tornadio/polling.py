import logging

from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import session, pollingsession

class TornadioPollingHandlerBase(RequestHandler):
    _sessions = session.SessionContainer()

    def __init__(self, handler, session_id):
        self.handler = handler

        print 'Polling: %s' % session_id

        if not session_id:
            # TODO: Configurable session expiration
            self.session = self._create_session(handler.connection)
        else:
            self.session = self._get_session(session_id)

            if self.session is None:
                # TODO: Send back disconnect message?
                raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self).__init__(handler.application,
                                                         handler.request)

    @classmethod
    def _session_expired(cls, session):
        session.item.on_close()

    @classmethod
    def _create_session(cls, connection):
        worker = pollingsession.PollingSession(connection)

        # TODO: Configurable timeouts
        session = cls._sessions.create(worker,
                                       expiry=15,
                                       on_delete=cls._session_expired)

        # TODO: Fix me - move to worker class
        # Send session id
        worker.send(session.session_id)

        worker.on_open()

        return worker

    @classmethod
    def _get_session(cls, session_id):
        session = cls._sessions.get(session_id)

        if session is None:
            return None

        return session.item

    @asynchronous
    def get(self, *args, **kwargs):
        raise NotImplemented()

    @asynchronous
    def post(self, *args, **kwargs):
        raise NotImplemented()

    def send(self, message):
        "Public send() function"
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

        self.session.flush()

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
        self.session.remove_handler(self)

    # TODO: Async
    def data_available(self, worker):
        # Encode message
        message = self.session.dump_messages()

        self.preflight()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Notify session that there's no handler waiting
        self.session.remove_handler(self)
