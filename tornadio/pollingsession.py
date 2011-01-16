# -*- coding: utf-8 -*-
"""
    tornadio.pollingsession
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module implements polling session class.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
from tornadio import proto, session

class PollingSession(session.Session):
    """This class represents virtual protocol connection for polling transports.

    For disconnected protocols, like XHR-Polling, it will cache outgoing
    messages, if there is on going GET connection - will pass cached/current
    messages to the actual transport protocol implementation.
    """
    def __init__(self, session_id, expiry, connection, *args, **kwargs):
        # Initialize session
        super(PollingSession, self).__init__(session_id, expiry)

        # Set connection
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

    def on_delete(self, forced):
        """Called by the session management class when item is
        about to get deleted/expired. If item is getting expired,
        there is possibility to force rescheduling of the item
        somewhere in the future, so it won't be deleted.

        Rescheduling is used in case when there is on-going GET
        connection.
        """
        if not forced and self.handler is not None and not self.is_closed:
            self.promote()
        else:
            self.close()

    def set_handler(self, handler):
        """Associate request handler with this virtual connection.

        If there is already handler associated, it won't be changed.
        """
        if self.handler is not None:
            return False

        self.handler = handler

        # Promote session item
        self.promote()

        return True

    def remove_handler(self, handler):
        """Remove associated Tornado handler.

        Promotes session in the cache, so time between two calls can't
        be greater than 15 seconds (by default)
        """
        if self.handler != handler:
            # TODO: Assert
            return False

        self.handler = None

        # Promote session so session item will live a bit longer
        # after disconnection
        self.promote()

    def dump_messages(self):
        """Get list of the pending messages and clears queue
        """
        messages = proto.encode(self.send_queue)
        self.send_queue = []
        return messages

    def flush(self):
        """Send all pending messages to the associated request handler (if any)
        """
        if self.handler is None:
            # TODO: Assert
            return

        if not self.send_queue:
            return

        self.handler.data_available(self)
        self.send_queue = []

    # TODO: Asynchronous
    def send(self, message):
        """Append message to the queue
        """
        self.send_queue.append(message)

        # If we have running GET request - notify protocol implementation
        # that we have some data available
        if self.handler is not None:
            self.handler.data_available(self)

    def close(self):
        """Forcibly close connection and notify connection object about that.
        """
        if not self.connection.is_closed:
            # Notify that connection was closed
            self.connection.on_close()
            self.connection.is_closed = True

    @property
    def is_closed(self):
        """Check if connection was closed or not"""
        return self.connection.is_closed
