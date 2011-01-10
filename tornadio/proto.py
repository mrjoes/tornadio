try:
    import simplejson as json
except:
    import json

FRAME = '~m~'
HEARTBEAT = '~h~'
JSON = '~j~'

def encode(message):
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

def decode(data):
    messages = []

    print data
    idx = 0

    while data[idx:idx+3] == FRAME:
        # Skip frame
        idx += 3

        len_start = idx
        while data[idx].isdigit():
            idx += 1

        print '"%s"' % data[len_start:idx]

        msg_len = int(data[len_start:idx])

        msg_type = data[idx:idx + 3]

        # Skip message type
        idx += 3

        msg_data = data[idx:idx + msg_len]
        print msg_data

        if msg_type == JSON:
            msg_data = json.loads(data[3:], parse_float=Decimal)

        messages.append((msg_type, msg_data))

        idx += msg_len

    print messages

    return messages
