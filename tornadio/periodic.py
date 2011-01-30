# -*- coding: utf-8 -*-
"""
    tornadio.flashserver
    ~~~~~~~~~~~~~~~~~~~~

    This module implements customized PeriodicCallback from tornado with
    support of the sliding window.

    :copyright: (c) 2011 by the Serge S. Koval, see AUTHORS for more details.
    :license: Apache, see LICENSE for more details.
"""
import time, logging

class Callback(object):
    def __init__(self, callback, callback_time, io_loop):
        self.callback = callback
        self.callback_time = callback_time
        self.io_loop = io_loop
        self._running = False

    def calculate_next_run(self):
        return time.time() + self.callback_time / 1000.0

    def start(self, timeout=None):
        self._running = True

        if timeout is None:
            timeout = self.calculate_next_run()

        self.io_loop.add_timeout(timeout, self._run)

    def stop(self):
        self._running = False

    def _run(self):
        if not self._running:
            return

        next_call = None

        try:
            next_call = self.callback()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            logging.error("Error in periodic callback", exc_info=True)

        self.start(next_call)
