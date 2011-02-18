# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    Transport protocol router and main entry point for all socket.io clients.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import logging

from tornado import ioloop
from tornado.web import RequestHandler, HTTPError

from tornadio import persistent, polling, session

PROTOCOLS = {
    'websocket': persistent.TornadioWebSocketHandler,
    'flashsocket': persistent.TornadioFlashSocketHandler,
    'xhr-polling': polling.TornadioXHRPollingSocketHandler,
    'xhr-multipart': polling.TornadioXHRMultipartSocketHandler,
    'htmlfile': polling.TornadioHtmlFileSocketHandler,
    'jsonp-polling': polling.TornadioJSONPSocketHandler,
    }

DEFAULT_SETTINGS = {
    # Sessions check interval in seconds
    'session_check_interval': 15,
    # Session expiration in seconds
    'session_expiry': 30,
    # Heartbeat time in seconds. Do not change this value unless
    # you absolutely sure that new value will work.
    'heartbeat_interval': 12,
    # Enabled protocols
    'enabled_protocols': ['websocket', 'flashsocket', 'xhr-multipart',
                          'xhr-polling', 'jsonp-polling', 'htmlfile'],
    # XHR-Polling request timeout, in seconds
    'xhr_polling_timeout': 20,
    }


class SocketRouterBase(RequestHandler):
    """Main request handler.

    Manages creation of appropriate transport protocol implementations and
    passing control to them.
    """
    _connection = None
    _route = None
    _sessions = None
    _sessions_cleanup = None
    settings = None

    def _execute(self, transforms, *args, **kwargs):
        try:
            extra = kwargs['extra']
            proto_name = kwargs['protocol']
            proto_init = kwargs['protocol_init']
            session_id = kwargs['session_id']

            logging.debug('Incoming session %s(%s) Session ID: %s Extra: %s' % (
                proto_name,
                proto_init,
                session_id,
                extra
                ))

            # If protocol is disabled, raise HTTPError
            if proto_name not in self.settings['enabled_protocols']:
                raise HTTPError(403, 'Forbidden')

            protocol = PROTOCOLS.get(proto_name, None)

            if protocol:
                handler = protocol(self, session_id)
                handler._execute(transforms, *extra, **kwargs)
            else:
                raise Exception('Handler for protocol "%s" is not available' %
                                proto_name)
        except ValueError:
            # TODO: Debugging
            raise HTTPError(403, 'Forbidden')

    @property
    def connection(self):
        """Return associated connection class."""
        return self._connection

    @property
    def sessions(self):
        return self._sessions

    @classmethod
    def route(cls):
        """Returns prepared Tornado routes"""
        return cls._route

    @classmethod
    def tornadio_initialize(cls, connection, user_settings, resource,
                            io_loop=None, extra_re=None, extra_sep=None):
        """Initialize class with the connection and resource.

        Does all behind the scenes work to setup routes, etc. Partially
        copied from SocketTornad.IO implementation.
        """


        # Associate connection object
        cls._connection = connection

        # Initialize io_loop
        cls.io_loop = io_loop or ioloop.IOLoop.instance()

        # Associate settings
        settings = DEFAULT_SETTINGS.copy()

        if user_settings is not None:
            settings.update(user_settings)

        cls.settings = settings

        # Initialize sessions
        cls._sessions = session.SessionContainer()

        check_interval = settings['session_check_interval'] * 1000
        cls._sessions_cleanup = ioloop.PeriodicCallback(cls._sessions.expire,
                                                        check_interval,
                                                        cls.io_loop).start()

        # Copied from SocketTornad.IO with minor formatting
        if extra_re:
            if extra_re[0] != '(?P<extra>':
                extra_re = r'(?P<extra>%s)' % extra_re
            if extra_sep:
                extra_re = extra_sep + extra_re
        else:
            extra_re = "(?P<extra>)"

        proto_re = "(%s)" % "|".join(PROTOCOLS.keys())

        cls._route = (r"/(?P<resource>%s)%s/"
                      "(?P<protocol>%s)/?"
                      "(?P<session_id>[0-9a-zA-Z]*)/?"
                      "((?P<protocol_init>\d*?)|(?P<xhr_path>\w*?))/?"
                      "(?P<jsonp_index>\d*?)" % (resource,
                                                 extra_re,
                                                 proto_re),
                      cls)

def get_router(handler, settings=None, resource='socket.io/*',
               io_loop=None, extra_re=None, extra_sep=None):
    """Create new router class with desired properties.

    Use this function to create new socket.io server. For example:

       class PongConnection(SocketConnection):
           def on_message(self, message):
               self.send(message)

       PongRouter = get_router(PongConnection)

       application = tornado.web.Application([PongRouter.route()])
    """
    router = type('SocketRouter', (SocketRouterBase,), {})
    router.tornadio_initialize(handler, settings, resource,
                               io_loop, extra_re, extra_sep)
    return router
