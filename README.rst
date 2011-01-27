========
Tornadio
========

Contributors
------------

 - `Serge S. Koval <https://github.com/MrJoes/>`_

Credits
-------

Authors of SocketTornad.IO project:

 - Brendan W. McAdams bwmcadams@evilmonkeylabs.com
 - `Matt Swanson <http://github.com/swanson>`_

This is implementation of the `Socket.IO <http://socket.io>` realtime
transport library on top of the `Tornado <http://www.tornadoweb.org>` framework.

Short Background
----------------

There's already library that implements Socket.IO integration with Tornado
framework - `SocketTornad.IO <http://github.com/SocketTornad.IO/>`, but
it was not finished. Also, I did not like how it is designed, so instead
of writing patches for the original library, decided to implement one
from scratch.

TornadIO is different from SocketTornad.IO library in following aspects:

 - Simpler internal design, easier to maintain/extend
 - No external dependencies (except of the Tornado itself and simplejson on python < 2.6)
 - Properly handles on_open/on_close events for polling transports
 - Proper Socket.IO protocol parser
 - Proper unicode support
 - Actively maintained

Introduction
------------

In order to start working with the TornadIO library, you need to know some basic concepts
on how Tornado works. If you don't, please read Tornado tutorial, which can be found
`here <http://www.tornadoweb.org/documentation#tornado-walk-through>`.

If you're familiar with Tornado, do following to add support for Socket.IO to your application:

1. Derive from tornadio.SocketConnection class and override on_message method (on_open/on_close are optional)::

  class MyConnection(tornadio.SocketConnection):
    def on_message(self, message):
      pass

2. Create handler object that will handle all `socket.io` transport related functionality::

  MyRouter = tornadio.get_router(MyConnection)

3. Add your handler routes to the Tornado application::

  application = tornado.web.Application(
    [MyRouter.route()],
    socket_io_port = 8000)

4. Start your application
5. You have your `socket.io` server running at port 8000. Simple, right?

Goodies
-------

``SocketConnection`` class implements three overridable methods:

1. ``on_open`` called when new client connection was established.
2. ``on_message`` called when message was received from the client. If client sent JSON object,
   it will be automatically decoded into appropriate Python data structures.
3. ``on_close`` called when client connection was closed (due to network error or timeout)


Each ``SocketConnection`` has ``send()`` method which is used to send data to this client. Input parameter
can be one of the:

1. String/unicode string - sent as is (though with utf-8 encoding)
2. Arbitrary python object - encoded as JSON string automatically
3. List of python objects/strings - encoded as series of the socket.io messages using one of the rules above.

Configuration
-------------

You can configure your handler by passing settings to the ``get_router`` function as a ``dict`` object.

-  **enabled_protocols**: This is a ``list`` of the socket.io protocols the server will respond requests for.
   Possibilities are:
-  *websocket*: HTML5 WebSocket transport
-  *flashsocket*: Flash emulated websocket transport. Requires Flash policy server running on port 843.
-  *xhr-multipart*: Works with two connections - long GET connection with multipart transfer encoding to receive
   updates from the server and separate POST requests to send data from the client.
-  *xhr-polling*: Long polling AJAX request to read data from the server and POST requests to send data to the server.
   If message is available, it will be sent through open GET connection (which is then closed) or queued on the
   server otherwise.
-  *jsonp-polling*: Similar to the *xhr-polling*, but pushes data through the JSONp.
-  *htmlfile*: IE only. Creates HTMLFile control which reads data from the server through one persistent connection.
   POST requests are used to send data back to the server.


-  **session_check_interval**: Specifies how often TornadIO will check session container for expired session objects.
   In seconds.
-  **session_expiry**: Specifies session expiration interval, in seconds. For polling transports it is actually
   maximum time allowed between GET requests to consider virtual connection closed.
-  **heartbeat_interval**: Heartbeat interval for persistent transports. Specifies how often heartbeat events should
   be sent from the server to the clients.
-  **xhr_polling_timeout**: Timeout for long running XHR connection for *xhr-polling* transport, in seconds. If no
   data was available during this time, connection will be closed on server side to avoid client-side timeouts.

Starting Up
-----------

Best Way: SocketServer
^^^^^^^^^^^^^^^^^^^^^^

We provide customized version (shamelessly borrowed from the SocketTornad.IO library) of the HttpServer, which
simplifies start of the your TornadIO server.

To start it, do following (assuming you created application object before)::

  if __name__ == "__main__":
    socketio_server = SocketServer(application)

Examples
--------

Chatroom Example
^^^^^^^^^^^^^^^^

There is a chatroom example application from the SocketTornad.IO library, contributed by
`swanson <http://github.com/swanson>`_. It is in the ``examples/chatroom`` directory.

Ping Example
^^^^^^^^^^^^

Simple ping/pong example to measure network performance. It is in the ``examples/ping`` directory.

Transports Example
^^^^^^^^^^^^^^^^^^

Simple ping/pong example with chat-like interface with selectable transports. It is in the
``examples/transports`` directory.
