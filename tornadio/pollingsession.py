from tornadio import proto, session

class PollingSession(session.Session):
    def __init__(self, session_id, expiry, connection, *args, **kwargs):
        # Initialize session
        super(PollingSession, self).__init__(session_id, expiry)

        self.connection = connection(self)
        self.handler = None
        self.send_queue = []

        # Forward some methods to connection
        self.on_open = self.connection.on_open
        self.raw_message = self.connection.raw_message
        self.on_close = self.connection.on_close

        self.reset_heartbeat = self.connection.reset_heartbeat
        self.stop_heartbeat = self.connection.stop_heartbeat

        # Send session_id
        self.send(session_id)

        # Notify that channel was opened
        self.on_open(*args, **kwargs)

    def on_delete(self):
        if self.handler is not None:
            self.promote()

    def set_handler(self, handler):
        if self.handler is not None:
            return False

        self.handler = handler

        self.promote()

        return True

    def remove_handler(self, handler):
        print 'Remove handler...'

        if self.handler != handler:
            print 'Wrong handler'
            # TODO: Assert
            return False

        self.handler = None

        # Promote session so it will live a bit longer after disconnection
        self.promote()

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
