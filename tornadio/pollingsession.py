from tornadio import proto

class PollingSession(object):
    def __init__(self, connection, *args, **kwargs):
        self.connection = connection(self)
        self.handler = None
        self.send_queue = []

        # Forward some events
        self.on_open = self.connection.on_open
        self.raw_message = self.connection.raw_message
        self.on_close = self.connection.on_close

    def set_handler(self, handler):
        if self.handler is not None:
            return False
        self.handler = handler
        return True

    def remove_handler(self, handler):
        if self.handler != handler:
            # TODO: Assert
            return False
        self.handler = None

    def dump_messages(self):
        messages = proto.encode(self.send_queue)
        self.send_queue = []
        return messages

    def flush(self):
        if self.handler is None:
            # TODO: Assert
            pass

        if not self.send_queue:
            return

        self.handler.data_available(self)
        self.send_queue = []

    # TODO: Asynchronous
    def send(self, message):
        self.send_queue.append(message)

        if self.handler is not None:
            self.handler.data_available(self)
