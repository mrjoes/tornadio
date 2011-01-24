from os import path as op

import tornado.web
import tornadio
import tornadio.router
import tornadio.server

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("index.html")

class ChatConnection(tornadio.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, *args, **kwargs):
        self.send("Welcome from the server.")

    def on_message(self, message):
        # Pong message back
        self.send(message)

#use the routes classmethod to build the correct resource
ChatRouter = tornadio.get_router(ChatConnection)

#configure the Tornado application
application = tornado.web.Application(
    [(r"/", IndexHandler), ChatRouter.route()],
    flash_policy_port = 843,
    flash_policy_file = op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port = 8001
)

if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    tornadio.server.SocketServer(application)

