# -*- coding: utf-8 -*-
"""
    tornadio.proto
    ~~~~~~~~~~~~~~

    Socket.IO 0.6.x protocol codec.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
try:
    import simplejson as json
except ImportError:
    import json

FRAME = '~m~'
HEARTBEAT = '~h~'
JSON = '~j~'

def encode(message):
    """Encode message to the socket.io wire format.

    1. If message is list, it will encode each separate list item as a message
    2. If message is a unicode or ascii string, it will be encoded as is
    3. If message some arbitrary python object or a dict, it will be JSON
    encoded
    """
    encoded = ''
    if isinstance(message, list):
        for msg in message:
            encoded += encode(msg)
    elif (not isinstance(message, (unicode, str))
          and isinstance(message, (object, dict))):
        if message is not None:
            encoded += encode('~j~' + json.dumps(message, use_decimal=True))
    else:
        msg = message.encode('utf-8')
        encoded += "%s%d%s%s" % (FRAME, len(msg), FRAME, msg)

    return encoded

def decode(data):
    """Decode socket.io messages

    Returns message tuples, first item in a tuple is message type (see
    message declarations in the beginning of the file) and second item
    is decoded message.
    """
    messages = []

    idx = 0

    while data[idx:idx+3] == FRAME:
        # Skip frame
        idx += 3

        len_start = idx
        while data[idx].isdigit():
            idx += 1

        msg_len = int(data[len_start:idx])

        msg_type = data[idx:idx + 3]

        # Skip message type
        idx += 3

        msg_data = data[idx:idx + msg_len]

        if msg_data.startswith(JSON):
            msg_data = json.loads(msg_data[3:])
        elif msg_data.startswith(HEARTBEAT):
            msg_type = HEARTBEAT
            msg_data = msg_data[3:]

        messages.append((msg_type, msg_data))

        idx += msg_len

    return messages
