"""Single-process polling hook for the native and container WSGI servers."""
import logging
import time
from wsgiref.simple_server import WSGIServer
from awesome_stock.storage import owner_schedule


class ScheduledOwnerServer(WSGIServer):
    def service_actions(self):
        now = time.monotonic()
        if now < getattr(self, '_next_schedule_poll', 0):
            return
        self._next_schedule_poll = now + 30
        try:
            owner_schedule.tick(self.get_app().store)
        except Exception:
            # A database-wide failure cannot reliably be recorded in that same
            # database. Keep polling, without logging credentials or payloads.
            logging.getLogger(__name__).error('Local daily scheduler unavailable; retrying on next poll')
