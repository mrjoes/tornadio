from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    def __init__(self, handler, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.handler = conn
        self.connection = handler.connection(self)

        super(TornadioWebSocketHandler, self).__init__(conn.application,
                                                       conn.request)

    def open(self, *args, **kwargs):
        self.connection.on_open(*args, **kwargs)

    def on_message(self, message):
        self.connection.raw_message(message)

    def on_close(self):
        self.connection.on_close()

    def send(self, message):
        self.async_callback(self.write_message)(proto.encode(message))

def TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, conn, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(conn, session_id)
