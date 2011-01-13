import logging

from tornado.web import RequestHandler, HTTPError, asynchronous

from tornadio import session

class TornadioPollingHandlerBase(RequestHandler):
    def __init__(self, conn, session_id):
        self.conn = conn

        if session_id is None:
            # TODO: Configurable session expiration
            self.worker = PollingWorkerFactory.create(conn.handler)
        else:
            self.worker = PollingWorkerFactory.get(session_id)

            if self.worker is None:
                # TODO: Send back disconnect message?
                raise HTTPError(401, 'Invalid session')

        super(TornadioPollingHandlerBase, self).__init__(conn.application,
                                                         conn.request)

    @asynchronous
    def get(self, *args, **kwargs):
        raise NotImplemented()

    @asynchronous
    def post(self, *args, **kwargs):
        raise NotImplemented()

    def send(self, message):
        "Public send() function"
        raise NotImplemented()

    def _write(self, message):
        "Called by the session when message is available"
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
        self.worker.set_handler(self.handler)
        self.worker.flush()

    @asynchronous
    def post(self, *args, **kwargs):
        self.set_header('Content-Type', 'text/plain')
        data = self.get_argument('data')
        if not self.preflight():
            raise HTTPError(401, 'unauthorized')

        # TODO: async
        self.worker.on_message(data.decode('utf-8', 'replace'))

        self.write('ok')
        self.finish()

    def on_connection_close(self):
        self.worker.remove_handler(self)

    def _write(self, message):
        self.preflight()
        self.set_header("Content-Type", "text/plain; charset=UTF-8")
        self.set_header("Content-Length", len(message))
        self.write(message)
        self.finish()

        # Notify session that there's no handler waiting
        self.worker.remove_handler(self)
