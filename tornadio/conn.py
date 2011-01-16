from tornado import ioloop

from tornadio import proto

class SocketConnection(object):
    def __init__(self, protocol):
        self._protocol = protocol

        # Initialize heartbeats
        self._heartbeat_timer = None
        self._heartbeats = 0

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
                # TODO: Verify
                print 'Incoming Heartbeat'

    # Heartbeat management
    def reset_heartbeat(self):
        print 'Reset HB'
        self.stop_heartbeat()

        self._heartbeat_timer = ioloop.PeriodicCallback(self._heartbeat, 12000)
        self._heartbeat_timer.start()

    def stop_heartbeat(self):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def _heartbeat(self):
        print 'Sending HB'

        self._heartbeats += 1
        self.send('~h~%d' % self._heartbeats)
