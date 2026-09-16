import os
import json
import time
from queue import Empty
from flask import Flask, render_template, request, jsonify, Response
from app.logger import broadcaster, install_logger_hooks
from app.scheduler import ContentScheduler
from app.watcher import QueueWatcher

# Install stdout/stderr log capture hooks
install_logger_hooks()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "tiktok-ups-orchestrator-key"

# Global Singletons
scheduler = ContentScheduler(processed_dir=os.getenv("PROCESSED_DIR", "Processed"))
watcher = QueueWatcher(
    queue_dir=os.getenv("QUEUE_DIR", "Queue"),
    scheduler_callback=scheduler.add_queue_item
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    status = scheduler.get_status()
    status["queue_dir"] = str(watcher.queue_dir)
    status["processed_dir"] = str(scheduler.processed_dir)
    return jsonify(status)

@app.route("/api/queue", methods=["GET"])
def get_queue():
    items = scheduler.get_queue()
    return jsonify(items)

@app.route("/api/queue/clear", methods=["POST"])
def clear_queue():
    scheduler.clear_completed()
    return jsonify({"success": True, "message": "Purged completed queue items."})

@app.route("/api/schedule", methods=["POST"])
def update_schedule():
    data = request.get_json(force=True, silent=True) or {}
    tiktok_enabled = data.get("tiktok_enabled")
    instagram_enabled = data.get("instagram_enabled")
    scheduled_datetime = data.get("scheduled_datetime")
    
    scheduler.update_config(
        tiktok_enabled=tiktok_enabled,
        instagram_enabled=instagram_enabled,
        scheduled_datetime_str=scheduled_datetime
    )
    return jsonify({"success": True, "status": scheduler.get_status()})

@app.route("/api/trigger", methods=["POST"])
def trigger_dispatch():
    data = request.get_json(force=True, silent=True) or {}
    item_id = data.get("item_id")
    
    if item_id:
        ok, msg = scheduler.dispatch_item(item_id)
        return jsonify({"success": ok, "message": msg})
    else:
        scheduler.dispatch_all_pending()
        return jsonify({"success": True, "message": "Dispatched all pending queue items."})

@app.route("/api/logs", methods=["GET"])
def stream_logs():
    """Server-Sent Events (SSE) streaming endpoint."""
    def generate():
        q = broadcaster.subscribe()
        try:
            # Send initial keepalive
            yield f": keepalive\n\n"
            while True:
                try:
                    record = q.get(timeout=20.0)
                    yield f"data: {json.dumps(record)}\n\n"
                except Empty:
                    # Send comment heartbeat to keep connection alive
                    yield f": ping\n\n"
        except (GeneratorExit, ConnectionResetError, BrokenPipeError, OSError):
            # Client disconnected or refreshed tab
            pass
        except Exception:
            pass
        finally:
            broadcaster.unsubscribe(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    broadcaster.clear()
    return jsonify({"success": True})

def start_services():
    scheduler.start()
    watcher.start()

def stop_services():
    watcher.stop()
    scheduler.stop()
