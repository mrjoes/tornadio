from tornadio import proto

class SocketConnection(object):
    def __init__(self, protocol):
        self._protocol = protocol

    def on_open(self, *args, **kwargs):
        pass

    def on_message(self, message):
        raise NotImplementedError()

    def on_close(self):
        pass

    def send(self, message):
        self._protocol.send(message)

    def close(self):
        self._protocol.close()

    def raw_message(self, message):
        for m in proto.decode(message):
            if m[0] == proto.FRAME or m[0] == proto.JSON:
                self.on_message(m[1])
            elif m[0] == proto.HEARTBEAT:
                logging.debug('Heartbeat')
