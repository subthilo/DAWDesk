from datetime import datetime

class BrokerLogger:
    def __init__(self):
        self.callbacks = []

    def log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        for cb in self.callbacks:
            try:
                cb(line)
            except Exception:
                pass

logger = BrokerLogger()

def _log(msg: str):
    logger.log(msg)
