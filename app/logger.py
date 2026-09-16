import sys
import time
import json
import logging
import threading
from collections import deque
from datetime import datetime
from queue import Queue, Empty

class LogBroadcaster:
    """Thread-safe stdout/stderr broadcaster that feeds an SSE ring buffer and live subscribers."""
    
    def __init__(self, max_history=1000):
        self.history = deque(maxlen=max_history)
        self.subscribers = set()
        self.lock = threading.Lock()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def emit(self, text, level="INFO"):
        if not text:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = text.splitlines()
        
        with self.lock:
            for line in lines:
                if not line.strip():
                    continue
                record = {
                    "timestamp": timestamp,
                    "level": level,
                    "message": line
                }
                self.history.append(record)
                
                # Push to subscribers
                dead_subs = set()
                for q in list(self.subscribers):
                    try:
                        q.put_nowait(record)
                    except Exception:
                        dead_subs.add(q)
                self.subscribers.difference_update(dead_subs)

    def subscribe(self):
        q = Queue(maxsize=500)
        with self.lock:
            # Pre-populate with recent history
            for record in self.history:
                try:
                    q.put_nowait(record)
                except Exception:
                    break
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.subscribers.discard(q)

    def clear(self):
        with self.lock:
            self.history.clear()


broadcaster = LogBroadcaster()


class StreamCapture:
    """Redirects writes to stdout/stderr while broadcasting to broadcaster."""
    def __init__(self, original_stream, level="INFO"):
        self.original_stream = original_stream
        self.level = level

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass
        broadcaster.emit(text, level=self.level)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass


class BroadcastHandler(logging.Handler):
    """Logging handler that pipes standard library logs to the broadcaster."""
    def emit(self, record):
        try:
            msg = self.format(record)
            broadcaster.emit(msg, level=record.levelname)
        except Exception:
            pass


def install_logger_hooks():
    """Hooks sys.stdout, sys.stderr, and the root logger."""
    sys.stdout = StreamCapture(broadcaster.original_stdout, level="INFO")
    sys.stderr = StreamCapture(broadcaster.original_stderr, level="ERROR")
    
    root = logging.getLogger()
    handler = BroadcastHandler()
    formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)
