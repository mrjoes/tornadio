import logging

from tornado.websocket import WebSocketHandler

from tornadio import proto

class TornadioWebSocketHandler(WebSocketHandler):
    def __init__(self, handler, session_id):
        logging.debug('Initializing WebSocket handler...')

        self.handler = handler
        self.connection = handler.connection(self)

        super(TornadioWebSocketHandler, self).__init__(handler.application,
                                                       handler.request)

    def open(self, *args, **kwargs):
        self.connection.on_open(*args, **kwargs)

        self.connection.reset_heartbeat()

    def on_message(self, message):
        self.connection.raw_message(message)

    def on_close(self):
        self.connection.on_close()

        self.connection.stop_heartbeat()

    def send(self, message):
        self.async_callback(self.write_message)(proto.encode(message))

        # TODO: If we're still connected - reset heartbeat
        #if self.request.connection.stream.socket:
        #    self.connection.reset_heartbeat()

def TornadioFlashSocketHandler(TornadioWebSocketHandler):
    def __init__(self, handler, session_id):
        logging.debug('Initializing FlashSocket handler...')

        super(TornadioFlashSocketHandler, self).__init__(handler, session_id)
