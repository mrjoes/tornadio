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

class SessionContainer(object):
    _items = dict()
    _queue = []

    def _random_key(self):
        m = md5()
        m.update('%s%s' % (random(), time()))
        return m.hexdigest()

    def create(self, expiry=None, on_delete=None):
        session = Session(self._random_key(), expiry, on_delete)
        self._items[session.session_id] = session

        if expiry is not None:
            heappush(self._queue, session)

        return session

    def get(self, session_id, promote=True):
        session = self._items.get(session_id, None)

        if session is not None and promote:
            session.promote()

        return session

    def remove(self, session_id):
        session = self._items.get(session_id, None)

        if session is not None:
            del self._items[session_id]
            session._item_deleted()
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

            # If item is promoted and expiration time somewhere in future
            # just reschedule it
            if top.promoted is not None and top.promoted > current_time:
                top.current_time = top.promoted
                top.promoted = None
                heappush(self._queue, top)
            else:
                # Otherwise - remove session
                del self._items[top.session_id]
                top._item_deleted()

def test():
    tot_t = 0
    tot_c = 0

    session = SessionContainer()

    while True:
        for j in xrange(0, 1000):
            op = randint(0, 5)

            if op == 0:
                session.create(30)
            elif op == 1 and session._queue:
                idx = randint(0, len(session._queue) - 1)
                item = session._queue[idx]
                item.promote()
        sleep(randint(0,2))

        t = time()

        print 'Before: %d' % (len(session._queue))

        start = clock()

        session.expire(t)

        delta = clock() - start
        tot_t += delta
        tot_c += 1

        print 'Queue size: %d, %f, %f' % (len(session._queue), delta, tot_t/tot_c)

        nl = []
        idx = 0
        errored = False
        while sesion._queue:
            x = heappop(sesion._queue)

            if t > x.expiry_date:
                print 'Error: (%d) %f vs %s' % (idx, t, x)
                errored = True

            nl.append(x)
            idx += 1;

        if errored:
            import pdb
            pdb.set_trace()

        heapify(nl)
        sesion._queue = nl

if __name__ == "__main__":
    test()
