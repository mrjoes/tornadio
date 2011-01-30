# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    For now, just sets debug level.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

version_info = (0,0,2)
version = '%d.%d.%d' % version_info

from tornadio.conn import SocketConnection
from tornadio.router import get_router
