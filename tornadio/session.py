from heapq import heappush, heappop, heapify
from time import time, sleep, clock
from hashlib import md5
from random import random, randint

class Session(object):
    def __init__(self, session_id, expiry=None, on_delete=None):
        self.session_id = session_id
        self._items = dict()
        self.promoted = None
        self.expiry = expiry
        self.on_delete = on_delete
        if self.expiry is not None:
            self.expiry_date = time() + self.expiry

    def promote(self):
        if self.expiry is not None:
            self.promoted = time() + self.expiry

    def _item_deleted(self):
        self.promoted = -1

        if self.on_delete is not None:
            self.on_delete()

    def get(self, key, default=None):
        return self._items.get(key, default)

    def set(self, key, value):
        self._items[key] = value

    def __cmp__(self, other):
        return cmp(self.expiry_date, other.expiry_date)

    def __repr__(self):
        return '%f %s %d' % (getattr(self, 'expiry_date', -1), self.session_id, self.promoted or 0)

class SessionManager(object):
    _items = dict()
    _queue = []

    @classmethod
    def _random_key(cls):
        m = md5()
        m.update('%s%s' % (random(), time()))
        return m.hexdigest()

    @classmethod
    def create(cls, expiry=None, on_delete=None):
        session = Session(cls._random_key(), expiry, on_delete)
        cls._items[session.session_id] = session

        if expiry is not None:
            heappush(cls._queue, session)

        return session

    @classmethod
    def get(cls, session_id, promote=True):
        session = cls._items.get(session_id, None)

        if session is not None and promote:
            session.promote()

        return session

    @classmethod
    def remove(cls, session_id):
        session = cls._items.get(session_id, None)

        if session is not None:
            del cls._items[session_id]
            session._item_deleted()
            return True

        return False

    @classmethod
    def expire(cls, current_time=None):
        if not cls._queue:
            return

        if current_time is None:
            current_time = time()

        while cls._queue:
            # Top most item is not expired yet
            top = cls._queue[0]

            # Early exit if item was not promoted and its expiration time
            # is greater than now.
            if top.promoted is None and top.expiry_date > current_time:
                break

            # Pop item from the stack
            top = heappop(cls._queue)

            # If item is promoted and expiration time somewhere in future
            # just reschedule it
            if top.promoted is not None and top.promoted > current_time:
                top.current_time = top.promoted
                top.promoted = None
                heappush(cls._queue, top)
            else:
                # Otherwise - remove session
                del cls._items[top.session_id]
                top._item_deleted()

def test():
    tot_t = 0
    tot_c = 0

    while True:
        for j in xrange(0, 1000):
            op = randint(0, 5)

            if op == 0:
                SessionManager.create(30)
            elif op == 1 and SessionManager._queue:
                idx = randint(0, len(SessionManager._queue) - 1)
                item = SessionManager._queue[idx]
                item.promote()
        sleep(randint(0,2))

        t = time()

        print 'Before: %d' % (len(SessionManager._queue))

        start = clock()

        SessionManager.expire(t)

        delta = clock() - start
        tot_t += delta
        tot_c += 1

        print 'Queue size: %d, %f, %f' % (len(SessionManager._queue), delta, tot_t/tot_c)

        nl = []
        idx = 0
        errored = False
        while SessionManager._queue:
            x = heappop(SessionManager._queue)

            if t > x.expiry_date:
                print 'Error: (%d) %f vs %s' % (idx, t, x)
                errored = True

            nl.append(x)
            idx += 1;

        if errored:
            import pdb
            pdb.set_trace()

        heapify(nl)
        SessionManager._queue = nl

if __name__ == "__main__":
    test()
