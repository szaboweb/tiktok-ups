import os
import time
import shutil
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from app.engines.tiktok_engine import upload_to_tiktok
from app.engines.instagram_engine import upload_to_instagram

logger = logging.getLogger("ContentScheduler")

class ContentScheduler:
    """Manages content queue, platform toggles, scheduling conditions, and upload dispatch."""

    def __init__(self, processed_dir="Processed"):
        self.processed_dir = Path(processed_dir).resolve()
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # State
        self.tiktok_enabled = True
        self.instagram_enabled = True
        self.scheduled_time = None  # datetime object or None
        self.scheduled_time_str = ""  # ISO format string for UI
        
        self.queue_items = []  # List of dicts
        self.lock = threading.Lock()
        
        self._running = False
        self._worker_thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        logger.info("[SCHEDULER] Scheduler worker initialized.")
        self._worker_thread = threading.Thread(target=self._schedule_loop, daemon=True, name="SchedulerWorkerThread")
        self._worker_thread.start()

    def stop(self):
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        logger.info("[SCHEDULER] Scheduler worker terminated.")

    def add_queue_item(self, file_path, filename, file_size_mb, description, hashtags, model_used):
        with self.lock:
            # Check if file is already queued
            for item in self.queue_items:
                if item["file_path"] == file_path and item["status"] in ["PENDING", "SCHEDULED"]:
                    return item["id"]

            item_id = f"item_{int(time.time() * 1000)}"
            record = {
                "id": item_id,
                "file_path": file_path,
                "filename": filename,
                "file_size_mb": file_size_mb,
                "description": description,
                "hashtags": hashtags,
                "model_used": model_used,
                "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "SCHEDULED" if self.scheduled_time else "PENDING",
                "results": {}
            }
            self.queue_items.append(record)
            logger.info(f"[SCHEDULER] Registered new queue item '{filename}' [ID: {item_id}]")
            return item_id

    def update_config(self, tiktok_enabled=None, instagram_enabled=None, scheduled_datetime_str=None):
        with self.lock:
            if tiktok_enabled is not None:
                self.tiktok_enabled = bool(tiktok_enabled)
                logger.info(f"[SCHEDULER] TikTok engine toggle updated: {self.tiktok_enabled}")
                
            if instagram_enabled is not None:
                self.instagram_enabled = bool(instagram_enabled)
                logger.info(f"[SCHEDULER] Instagram engine toggle updated: {self.instagram_enabled}")
                
            if scheduled_datetime_str is not None:
                self.scheduled_time_str = scheduled_datetime_str.strip()
                if self.scheduled_time_str:
                    try:
                        # Parse HTML datetime-local: "YYYY-MM-DDTHH:MM" or "YYYY-MM-DDTHH:MM:SS"
                        clean_str = self.scheduled_time_str.replace("T", " ")
                        if len(clean_str) == 16:
                            clean_str += ":00"
                        self.scheduled_time = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                        logger.info(f"[SCHEDULER] Content schedule target set to: {self.scheduled_time}")
                        # Mark pending items as SCHEDULED
                        for item in self.queue_items:
                            if item["status"] == "PENDING":
                                item["status"] = "SCHEDULED"
                    except Exception as e:
                        logger.error(f"[SCHEDULER] Failed to parse schedule datetime string '{scheduled_datetime_str}': {e}")
                        self.scheduled_time = None
                else:
                    self.scheduled_time = None
                    logger.info("[SCHEDULER] Content schedule target cleared (Immediate manual mode).")

    def get_status(self):
        with self.lock:
            return {
                "tiktok_enabled": self.tiktok_enabled,
                "instagram_enabled": self.instagram_enabled,
                "scheduled_time": self.scheduled_time_str,
                "is_scheduled": self.scheduled_time is not None,
                "queue_count": len(self.queue_items),
                "pending_count": sum(1 for x in self.queue_items if x["status"] in ["PENDING", "SCHEDULED"]),
                "processed_count": sum(1 for x in self.queue_items if x["status"] == "PROCESSED"),
                "failed_count": sum(1 for x in self.queue_items if x["status"] == "FAILED"),
            }

    def get_queue(self):
        with self.lock:
            return list(self.queue_items)

    def clear_completed(self):
        with self.lock:
            self.queue_items = [x for x in self.queue_items if x["status"] in ["PENDING", "SCHEDULED", "DISPATCHING"]]
            logger.info("[SCHEDULER] Purged completed and failed records from dashboard queue.")

    def dispatch_item(self, item_id: str):
        """Triggers immediate background dispatch for a specific queue item."""
        with self.lock:
            target = next((x for x in self.queue_items if x["id"] == item_id), None)
            if not target:
                return False, "Item not found"
            if target["status"] == "DISPATCHING":
                return False, "Item is already dispatching"
            target["status"] = "DISPATCHING"

        # Run upload in worker thread
        threading.Thread(target=self._execute_upload_pipeline, args=(target,), daemon=True).start()
        return True, "Dispatch initiated"

    def dispatch_all_pending(self):
        """Dispatches all items currently in PENDING or SCHEDULED state."""
        with self.lock:
            items_to_dispatch = [x for x in self.queue_items if x["status"] in ["PENDING", "SCHEDULED"]]
            for itm in items_to_dispatch:
                itm["status"] = "DISPATCHING"

        for itm in items_to_dispatch:
            threading.Thread(target=self._execute_upload_pipeline, args=(itm,), daemon=True).start()

    def _execute_upload_pipeline(self, item: dict):
        file_path = item["file_path"]
        filename = item["filename"]
        desc = item["description"]
        tags = item["hashtags"]
        
        logger.info(f"[SCHEDULER] >>> Commencing distribution pipeline for: {filename}")
        
        results = {}
        overall_success = True
        
        # 1. TikTok Engine
        if self.tiktok_enabled:
            logger.info(f"[SCHEDULER] Routing {filename} to TikTok Engine...")
            tk_ok, tk_msg = upload_to_tiktok(file_path, desc, tags)
            results["tiktok"] = {"success": tk_ok, "message": tk_msg}
            if not tk_ok:
                overall_success = False
        else:
            logger.info(f"[SCHEDULER] Skipping TikTok: Toggle is OFF.")
            results["tiktok"] = {"success": None, "message": "Platform disabled in orchestrator toggle"}

        # 2. Instagram Engine
        if self.instagram_enabled:
            logger.info(f"[SCHEDULER] Routing {filename} to Instagram Engine...")
            ig_ok, ig_msg = upload_to_instagram(file_path, desc, tags)
            results["instagram"] = {"success": ig_ok, "message": ig_msg}
            if not ig_ok:
                overall_success = False
        else:
            logger.info(f"[SCHEDULER] Skipping Instagram: Toggle is OFF.")
            results["instagram"] = {"success": None, "message": "Platform disabled in orchestrator toggle"}

        # Update item status
        with self.lock:
            item["results"] = results
            item["dispatched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            any_success = any(v.get("success") is True for v in results.values() if isinstance(v, dict))

            if any_success or overall_success:
                try:
                    dest_path = self.processed_dir / filename
                    if os.path.exists(file_path):
                        shutil.move(file_path, str(dest_path))
                        item["file_path"] = str(dest_path)
                        logger.info(f"[SCHEDULER] Relocated {filename} -> {self.processed_dir}")
                except Exception as e:
                    logger.warning(f"[SCHEDULER] Could not relocate file to Processed: {e}")

            if overall_success:
                item["status"] = "PROCESSED"
                logger.info(f"[SCHEDULER] <<< Finished distribution pipeline for: {filename} [STATUS: COMPLETED]")
            else:
                item["status"] = "FAILED"
                logger.error(f"[SCHEDULER] <<< Finished distribution pipeline for: {filename} [STATUS: PARTIAL/FAILED]")

    def _schedule_loop(self):
        while self._running:
            try:
                if self.scheduled_time:
                    now = datetime.now()
                    if now >= self.scheduled_time:
                        logger.info(f"[SCHEDULER] Target schedule condition reached ({self.scheduled_time}). Initiating automated dispatch...")
                        # Reset schedule time to avoid re-triggering repeatedly
                        self.scheduled_time = None
                        self.scheduled_time_str = ""
                        self.dispatch_all_pending()
            except Exception as e:
                logger.error(f"[SCHEDULER] Exception in schedule check loop: {e}")
                
            time.sleep(1.0)
