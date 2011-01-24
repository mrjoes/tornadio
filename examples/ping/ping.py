from os import path as op

from datetime import datetime

import tornado.web
import tornadio
import tornadio.router
import tornadio.server

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the ping page"""
    def get(self):
        self.render("index.html")

class PingConnection(tornadio.SocketConnection):
    def on_message(self, message):
        message['server'] = str(datetime.now())
        self.send(message)

#use the routes classmethod to build the correct resource
PingRouter = tornadio.get_router(PingConnection)

#configure the Tornado application
application = tornado.web.Application(
    [(r"/", IndexHandler), PingRouter.route()],
    enabled_protocols = ['websocket',
                         'flashsocket',
                         'xhr-multipart',
                         'xhr-polling'],
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    tornadio.server.SocketServer(application)
