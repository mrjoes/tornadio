import logging

from tornado import ioloop
from tornado.httpserver import HTTPServer

from tornadio.flashserver import FlashPolicyServer

class SocketServer(HTTPServer):
    """HTTP Server which does some configuration and automatic setup
    of Socket.IO based on configuration.
    Starts the IOLoop and listening automatically
    in contrast to the Tornado default behavior.
    If FlashSocket is enabled, starts up the policy server also."""

    def __init__(self, application, no_keep_alive=False, io_loop=None,
                 xheaders=False, ssl_options=None, socket_io_port=8888,
                 flash_policy_port=843, flash_policy_file='flashpolicy.xml',
                 enabled_protocols=['websocket', 'flashsocket', 'xhr-multipart',
                                    'xhr-polling', 'jsonp-polling', 'htmlfile']
                 ):
        """Initializes the server with the given request callback.

        If you use pre-forking/start() instead of the listen() method to
        start your server, you should not pass an IOLoop instance to this
        constructor. Each pre-forked child process will create its own
        IOLoop instance after the forking process.
        """
        sett = application.settings

        logging.debug('Starting up SocketIOServer with settings: %s' % sett)

        enabled_protocols = sett.get('enabled_protocols', ['websocket',
                                                           'flashsocket',
                                                           'xhr-multipart',
                                                           'xhr-polling',
                                                           'jsonp-polling',
                                                           'htmlfile'])
        flash_policy_file = sett.get('flash_policy_file', 'flashpolicy.xml')
        flash_policy_port = sett.get('flash_policy_port', 843)
        socket_io_port = sett.get('socket_io_port', 8888)

        HTTPServer.__init__(self,
                            application,
                            no_keep_alive,
                            io_loop,
                            xheaders,
                            ssl_options)

        logging.info('Starting up TornadIO Server on Port \'%s\'' %
                     socket_io_port)

        self.listen(socket_io_port)

        if 'flashsocket' in enabled_protocols:
            logging.info('Flash Sockets enabled, starting Flash Policy Server '
                         'on Port \'%s\'' % flash_policy_port)
            flash_policy = FlashPolicyServer(port = flash_policy_port,
                                             policy_file = flash_policy_file)

        io_loop = io_loop or ioloop.IOLoop.instance()
        logging.info("Entering IOLoop...")
        io_loop.start()
