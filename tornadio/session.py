# -*- coding: utf-8 -*-
"""
    tornadio.router
    ~~~~~~~~~~~~~~~

    Simple heapq-based session implementation with sliding expiration window
    support.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""

from heapq import heappush, heappop, heapify
from time import time, sleep, clock
from hashlib import md5
from random import random, randint

class Session(object):
    def __init__(self, session_id, expiry=None):
        self.session_id = session_id
        self.promoted = None
        self.expiry = expiry

        if self.expiry is not None:
            self.expiry_date = time() + self.expiry

    def promote(self):
        if self.expiry is not None:
            self.promoted = time() + self.expiry

    def on_delete(self, forced):
        pass

    def __cmp__(self, other):
        return cmp(self.expiry_date, other.expiry_date)

    def __repr__(self):
        return '%f %s %d' % (getattr(self, 'expiry_date', -1),
                             self.session_id,
                             self.promoted or 0)

class SessionContainer(object):
    def __init__(self):
        self._items = dict()
        self._queue = []

    def _random_key(self):
        m = md5()
        m.update('%s%s' % (random(), time()))
        return m.hexdigest()

    def create(self, session, expiry=None, **kwargs):
        kwargs['session_id'] = self._random_key()
        kwargs['expiry'] = expiry

        session = session(**kwargs)

        self._items[session.session_id] = session

        if expiry is not None:
            heappush(self._queue, session)

        return session

    def get(self, session_id):
        return self._items.get(session_id, None)

    def remove(self, session_id):
        session = self._items.get(session_id, None)

        if session is not None:
            self._items[session].promoted = -1
            session.on_delete(True)
            del self._items[session_id]
            return True

        return False

    def expire(self, current_time=None):
        if not self._queue:
            return

        if current_time is None:
            current_time = time()

        while self._queue:
            # Top most item is not expired yet
            top = self._queue[0]

            # Early exit if item was not promoted and its expiration time
            # is greater than now.
            if top.promoted is None and top.expiry_date > current_time:
                break

            # Pop item from the stack
            top = heappop(self._queue)

            need_reschedule = (top.promoted is not None
                               and top.promoted > current_time)

            # Give chance to reschedule
            if not need_reschedule:
                top.promoted = None
                top.on_delete(False)

                need_reschedule = (top.promoted is not None
                                   and top.promoted > current_time)

            # If item is promoted and expiration time somewhere in future
            # just reschedule it
            if need_reschedule:
                top.expiry_date = top.promoted
                top.promoted = None
                heappush(self._queue, top)
            else:
                del self._items[top.session_id]
