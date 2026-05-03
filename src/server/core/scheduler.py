import threading
import logging

logger = logging.getLogger(__name__)
_scheduler_started = False


def _scan_loop():
    while True:
        threading.Event().wait(10)


def start():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    t = threading.Thread(target=_scan_loop, daemon=True)
    t.start()
    logger.info("Scheduler started (10s tick)")
