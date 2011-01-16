from tornado.web import RequestHandler, HTTPError

from tornadio import persistent, polling

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    'xhr-polling': polling.TornadioXHRPollingSocketHandler,
    'xhr-multipart': polling.TornadioXHRMultipartSocketHandler,
    }

class SocketRouterBase(RequestHandler):
    _connection = None
    _route = None

    def _execute(self, transforms, *args, **kwargs):
        try:
            extra = kwargs['extra']
            proto_name = kwargs['protocol']
            proto_init = kwargs['protocol_init']
            session_id = kwargs['session_id']

            print 'Incoming session %s(%s) Session ID: %s Extra: %s' % (
                proto_name,
                proto_init,
                session_id,
                extra
                )

            protocol = PROTOCOLS.get(proto_name, None)

            # TODO: Enabled transports configuration
            if protocol:
                print protocol

                handler = protocol(self, session_id)
                handler._execute(transforms, *extra, **kwargs)
            else:
                raise Exception('Handler for protocol "%s" is not available' %
                                prot_name)
        except ValueError, e:
            print 'Malformed request: %s' % e
            raise HttpError(400)

    @property
    def connection(self):
        return self._connection

    @classmethod
    def route(cls):
        return cls._route

    @classmethod
    def _initialize(cls, connection, resource, extraRE=None, extraSep=None):
        cls._connection = connection

        # Copied from SocketTornad.IO with minor formatting
        if extraRE:
            if extraRE[0] != '(?P<extra>':
                if extraRE[0] == '(':
                    extraRE = r'(?P<extra>%s)' % extraRE
                else:
                    extraRE = r"(?P<extra>%s)" % extraRE
            if extraSep:
                extraRE = extraSep + extraRE
        else:
            extraRE = "(?P<extra>)"

        protoRE = "(%s)" % "|".join(PROTOCOLS.keys())

        cls._route = (r"/(?P<resource>%s)%s/"
                      "(?P<protocol>%s)/?"
                      "(?P<session_id>[0-9a-zA-Z]*)/?"
                      "((?P<protocol_init>\d*?)|(?P<xhr_path>\w*?))/?"
                      "(?P<jsonp_index>\d*?)" % (resource,
                                                 extraRE,
                                                 protoRE),
                      cls)

def get_router(handler, resource, extraRE=None, extraSep=None):
    router = type('SocketRouter', (SocketRouterBase,), {})
    router._initialize(handler, resource, extraRE, extraSep)
    return router
