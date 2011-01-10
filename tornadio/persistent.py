import logging

from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    def __init__(self, conn, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.conn = conn
        self.handler = conn.handler(self)

        print conn.application
        print conn.request

        super(TornadioWebSocketHandler, self).__init__(conn.application,
                                                       conn.request)

    def open(self, *args, **kwargs):
        logging.debug('on_open')
        self.handler.on_open(*args, **kwargs)

    def on_message(self, message):
        logging.debug('on_message')

        for m in proto.decode(message):
            if m[0] == proto.FRAME or m[0] == proto.JSON:
                self.handler.on_message(m[1])
            elif m[0] == proto.HEARTBEAT:
                logging.debug('Heartbeat')

    def on_close(self):
        logging.debug('on_close')

        self.handler.on_close()

    def send(self, message):
        self.async_callback(self.write_message)(proto.encode(message))

def TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, conn, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(conn, session_id)

