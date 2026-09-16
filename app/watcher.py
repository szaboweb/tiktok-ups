import os
import time
import logging
import threading
from pathlib import Path
from app.gemini_service import generate_video_copy_and_hashtags

logger = logging.getLogger("DirectoryWatcher")

class QueueWatcher:
    """Monitors the Queue directory for new .mp4 video files."""

    def __init__(self, queue_dir="Queue", scheduler_callback=None, poll_interval=2.0):
        self.queue_dir = Path(queue_dir).resolve()
        self.scheduler_callback = scheduler_callback
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None
        self._known_files = set()
        self._lock = threading.Lock()
        
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        if self._running:
            return
        self._running = True
        logger.info(f"[WATCHER] Initializing directory monitor on: {self.queue_dir}")
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="QueueWatcherThread")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("[WATCHER] Directory monitor stopped.")

    def _wait_for_file_settled(self, file_path: Path, max_wait_sec=10) -> bool:
        """Ensures file is fully written before processing."""
        start_time = time.time()
        last_size = -1
        
        while time.time() - start_time < max_wait_sec:
            try:
                if not file_path.exists():
                    return False
                current_size = file_path.stat().st_size
                if current_size > 0 and current_size == last_size:
                    # File size is stable, verify read handle
                    with open(file_path, "rb") as f:
                        f.read(1024)
                    return True
                last_size = current_size
            except (PermissionError, OSError):
                pass
            time.sleep(1.0)
            
        return file_path.exists() and file_path.stat().st_size > 0

    def _process_file(self, file_path: Path):
        filename = file_path.name
        logger.info(f"[WATCHER] New file detected in Queue: {filename}")
        
        if not self._wait_for_file_settled(file_path):
            logger.warning(f"[WATCHER] File write incomplete or inaccessible: {filename}")
            return
            
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        logger.info(f"[WATCHER] Video verified ({file_size_mb:.2f} MB). Triggering Gemini metadata pipeline...")
        
        try:
            metadata = generate_video_copy_and_hashtags(
                file_path=str(file_path),
                filename=filename,
                file_size_mb=file_size_mb
            )
            
            logger.info(f"[WATCHER] Generated Copy: \"{metadata['description']}\"")
            logger.info(f"[WATCHER] Structural Hashtags ({len(metadata['hashtags'])}): {' '.join(metadata['hashtags'])}")
            
            if self.scheduler_callback:
                self.scheduler_callback(
                    file_path=str(file_path),
                    filename=filename,
                    file_size_mb=file_size_mb,
                    description=metadata["description"],
                    hashtags=metadata["hashtags"],
                    model_used=metadata.get("model_used", "Gemini")
                )
        except Exception as e:
            logger.error(f"[WATCHER] Error processing {filename} through Gemini pipeline: {e}")

    def _poll_loop(self):
        logger.info(f"[WATCHER] Active. Monitoring queue folder: {self.queue_dir}")

        while self._running:
            try:
                current_mp4s = set()
                for item in self.queue_dir.glob("*"):
                    if item.is_file() and item.suffix.lower() == ".mp4":
                        current_mp4s.add(str(item.resolve()))
                        
                with self._lock:
                    new_files = current_mp4s - self._known_files
                    
                for new_file_str in new_files:
                    path_obj = Path(new_file_str)
                    if path_obj.exists():
                        self._process_file(path_obj)
                        with self._lock:
                            self._known_files.add(new_file_str)
                            
                # Clean up deleted files from known list
                with self._lock:
                    self._known_files = self._known_files.intersection(current_mp4s)
                    
            except Exception as e:
                logger.error(f"[WATCHER] Exception in polling cycle: {e}")
                
            time.sleep(self.poll_interval)
