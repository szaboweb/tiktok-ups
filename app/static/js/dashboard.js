/**
 * TIKTOK-UPS ORCHESTRATOR - DASHBOARD LOGIC
 * Strict Rule: ZERO EMOJIS in UI, messages, and elements.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const terminalScreen = document.getElementById("terminalScreen");
    const streamIndicator = document.getElementById("streamIndicator");
    const toggleAutoScrollBtn = document.getElementById("toggleAutoScrollBtn");
    const pauseStreamBtn = document.getElementById("pauseStreamBtn");
    const clearLogsBtn = document.getElementById("clearLogsBtn");

    const tiktokToggle = document.getElementById("tiktokToggle");
    const instagramToggle = document.getElementById("instagramToggle");
    const scheduleDatetime = document.getElementById("scheduleDatetime");
    const saveScheduleBtn = document.getElementById("saveScheduleBtn");
    const clearScheduleBtn = document.getElementById("clearScheduleBtn");
    const dispatchAllBtn = document.getElementById("dispatchAllBtn");
    const clearQueueBtn = document.getElementById("clearQueueBtn");
    const refreshQueueBtn = document.getElementById("refreshQueueBtn");

    const statQueueCount = document.getElementById("statQueueCount");
    const statPendingCount = document.getElementById("statPendingCount");
    const statProcessedCount = document.getElementById("statProcessedCount");
    const statFailedCount = document.getElementById("statFailedCount");
    const queueContainer = document.getElementById("queueContainer");
    const queueEmptyState = document.getElementById("queueEmptyState");

    // State
    let autoScroll = true;
    let streamPaused = false;
    let eventSource = null;

    // ======================================================
    // SSE Real-Time Terminal Log Stream
    // ======================================================
    function initLogStream() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource("/api/logs");

        eventSource.onopen = () => {
            streamIndicator.textContent = "LIVE (SSE)";
            streamIndicator.className = "node-val status-live";
        };

        eventSource.onmessage = (event) => {
            if (streamPaused) return;

            try {
                const record = JSON.parse(event.data);
                appendTerminalLine(record);
            } catch (e) {
                // Raw text fallback
                appendTerminalLine({
                    timestamp: new Date().toISOString().replace("T", " ").substring(0, 19),
                    level: "INFO",
                    message: event.data
                });
            }
        };

        eventSource.onerror = () => {
            streamIndicator.textContent = "DISCONNECTED";
            streamIndicator.className = "node-val status-active";
        };
    }

    function appendTerminalLine(record) {
        const line = document.createElement("div");
        line.className = "term-line";

        const ts = document.createElement("span");
        ts.className = "term-ts";
        ts.textContent = record.timestamp || "";

        const lvl = document.createElement("span");
        const levelStr = (record.level || "INFO").toUpperCase();
        lvl.className = `term-lvl term-lvl-${levelStr}`;
        lvl.textContent = `[${levelStr}]`;

        const msg = document.createElement("span");
        msg.className = "term-msg";
        msg.textContent = record.message || "";

        line.appendChild(ts);
        line.appendChild(lvl);
        line.appendChild(msg);
        terminalScreen.appendChild(line);

        if (autoScroll) {
            terminalScreen.scrollTop = terminalScreen.scrollHeight;
        }
    }

    // Terminal Controls
    toggleAutoScrollBtn.addEventListener("click", () => {
        autoScroll = !autoScroll;
        toggleAutoScrollBtn.textContent = `AUTO-SCROLL [${autoScroll ? "ON" : "OFF"}]`;
        toggleAutoScrollBtn.classList.toggle("active", autoScroll);
        if (autoScroll) {
            terminalScreen.scrollTop = terminalScreen.scrollHeight;
        }
    });

    pauseStreamBtn.addEventListener("click", () => {
        streamPaused = !streamPaused;
        pauseStreamBtn.textContent = streamPaused ? "RESUME STREAM" : "PAUSE STREAM";
        pauseStreamBtn.classList.toggle("active", streamPaused);
    });

    clearLogsBtn.addEventListener("click", async () => {
        terminalScreen.innerHTML = "";
        try {
            await fetch("/api/logs/clear", { method: "POST" });
        } catch (e) {
            console.error("Failed to clear server log buffer", e);
        }
    });

    // ======================================================
    // Status & Configuration
    // ======================================================
    async function loadStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();

            tiktokToggle.checked = data.tiktok_enabled;
            instagramToggle.checked = data.instagram_enabled;
            if (data.scheduled_time) {
                scheduleDatetime.value = data.scheduled_time;
            }

            statQueueCount.textContent = data.queue_count;
            statPendingCount.textContent = data.pending_count;
            statProcessedCount.textContent = data.processed_count;
            statFailedCount.textContent = data.failed_count;
        } catch (e) {
            console.error("Error fetching status", e);
        }
    }

    async function saveSchedule(clearDate = false) {
        const payload = {
            tiktok_enabled: tiktokToggle.checked,
            instagram_enabled: instagramToggle.checked,
            scheduled_datetime: clearDate ? "" : scheduleDatetime.value
        };

        try {
            const res = await fetch("/api/schedule", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success) {
                if (clearDate) {
                    scheduleDatetime.value = "";
                }
                loadStatus();
                loadQueue();
            }
        } catch (e) {
            console.error("Failed to update schedule", e);
        }
    }

    tiktokToggle.addEventListener("change", () => saveSchedule(false));
    instagramToggle.addEventListener("change", () => saveSchedule(false));
    saveScheduleBtn.addEventListener("click", () => saveSchedule(false));
    clearScheduleBtn.addEventListener("click", () => saveSchedule(true));

    // ======================================================
    // Queue & Execution Pipeline
    // ======================================================
    async function loadQueue() {
        try {
            const res = await fetch("/api/queue");
            const items = await res.json();

            // Clear previous cards except empty state
            const cards = queueContainer.querySelectorAll(".queue-card");
            cards.forEach(c => c.remove());

            if (!items || items.length === 0) {
                queueEmptyState.style.display = "flex";
                return;
            }

            queueEmptyState.style.display = "none";

            items.forEach(item => {
                const card = document.createElement("div");
                card.className = "queue-card";

                const top = document.createElement("div");
                top.className = "queue-card-top";

                const info = document.createElement("div");
                info.className = "card-file-info";
                info.innerHTML = `
                    <span class="card-filename">${escapeHtml(item.filename)}</span>
                    <span class="card-meta-sub">${item.file_size_mb.toFixed(2)} MB // Detected: ${item.detected_at} // Model: ${item.model_used}</span>
                `;

                const badge = document.createElement("span");
                const statusKey = (item.status || "PENDING").toLowerCase();
                badge.className = `card-status-badge badge-${statusKey}`;
                badge.textContent = item.status;

                top.appendChild(info);
                top.appendChild(badge);

                // Copy Block
                const copyBlock = document.createElement("div");
                copyBlock.className = "card-copy-block";
                copyBlock.innerHTML = `
                    <div class="copy-label">AI GENERATED COPY</div>
                    <div class="copy-text">${escapeHtml(item.description || "Pending copy generation...")}</div>
                `;

                // Hashtags
                const tagsRow = document.createElement("div");
                tagsRow.className = "hashtags-row";
                (item.hashtags || []).forEach(tag => {
                    const pill = document.createElement("span");
                    pill.className = "hashtag-pill";
                    pill.textContent = tag;
                    tagsRow.appendChild(pill);
                });
                copyBlock.appendChild(tagsRow);

                // Card Actions
                const actions = document.createElement("div");
                actions.className = "card-actions";
                
                if (item.status === "PENDING" || item.status === "SCHEDULED") {
                    const dispatchBtn = document.createElement("button");
                    dispatchBtn.className = "btn-micro";
                    dispatchBtn.textContent = "DISPATCH NOW";
                    dispatchBtn.onclick = () => triggerItem(item.id);
                    actions.appendChild(dispatchBtn);
                }

                card.appendChild(top);
                card.appendChild(copyBlock);
                if (actions.children.length > 0) {
                    card.appendChild(actions);
                }

                queueContainer.appendChild(card);
            });
        } catch (e) {
            console.error("Error loading queue", e);
        }
    }

    async function triggerItem(itemId) {
        try {
            await fetch("/api/trigger", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ item_id: itemId })
            });
            loadStatus();
            loadQueue();
        } catch (e) {
            console.error("Error triggering item", e);
        }
    }

    dispatchAllBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/trigger", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
            });
            loadStatus();
            loadQueue();
        } catch (e) {
            console.error("Error dispatching all", e);
        }
    });

    clearQueueBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/queue/clear", { method: "POST" });
            loadStatus();
            loadQueue();
        } catch (e) {
            console.error("Error clearing queue", e);
        }
    });

    refreshQueueBtn.addEventListener("click", () => {
        loadStatus();
        loadQueue();
    });

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // Polling sync interval for metrics and queue state
    setInterval(() => {
        loadStatus();
        loadQueue();
    }, 4000);

    // Initial load
    initLogStream();
    loadStatus();
    loadQueue();
});
