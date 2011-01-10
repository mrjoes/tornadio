FRAME = '~m~'
HEARTBEAT = '~h~'

class SocketIOProtocol(object):
    def _encode(self, message):
        encoded = ''
        if isinstance(message, list):
            for m in message:
                encoded += self._encode(m)
        elif not isinstance(message, (unicode, str)) and isinstance(message, (object, dict)):
            """
            Strings are objects... messy test.
            """
            if message is not None:
                encoded += self._encode('~j~' + json.dumps(message, use_decimal=True))
        else:
            encoded += "%s%d%s%s" % (FRAME, len(message), FRAME, message)

        return encoded

    def _decode(self, data):
        messages = []

        print data
        idx = 0

        while msg[idx:idx+3] == FRAME:
            # Skip frame
            idx += 3

            len_start = idx
            while msg[idx].isdigit():
                idx += 1

            msg_len = int(msg[len_start:idx])
            msg = data[idx:idx+len]

            messages.append(msg)

        parts = message.split(FRAME)[1:]
        for i in range(1, len(parts), 2):
            l = int(parts[i - 1])
            data = parts[i]
            if len(data) != l:
                # TODO - Fail on invalid length?
                logging.warning("Possibly invalid message. Expected length '%d', got '%d'" % (l, len(data)))

            # Check the frame for an internal message
            in_frame = data[:3]
            if in_frame == '~h~':
                # TODO: Support heartbeats
                #self.async_callback(self.on_heartbeat)(int(data[3:]))
                continue
            elif in_frame == '~j~':
                data = json.loads(data[3:], parse_float=Decimal)

            messages.append(data)

        return messages
