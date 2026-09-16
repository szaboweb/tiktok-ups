# tiktok-ups

A minimalist, self-hosted Scheduled Content Uploader for TikTok and Instagram Reels. 

This repository acts as an orchestrator application that connects a local shared storage pipeline to your social media channels. Before launching the system, read this guide to understand the underlying framework, architecture, and security protocols.

---

## Core Concepts & Process Flow

*   **Development Framework (Google Antigravity 2.0):** This is your core environment. It provides convenience tools and features an embedded AI coding agent. The agent executes the prompt instructions defined in the chat, coordinates files, and manages background tasks.
*   **Filesystem & Terminal:** The AI agent operates directly inside your laptop's filesystem. To deploy software modules or execute system commands, it runs instructions within the terminal (command-line interface).
*   **The Codebase:** The application code is written in Python. This script provides the exact technical logic telling the computer how to handle files and automate workflows.
*   **Debugging:** If the code fails or encounters a runtime error, a specific error log will appear in the terminal. Copy this traceback log, paste it into the agent chat, and request a fix. This cycle is called debugging.
*   **User Interface (UI) & Frontend:** The complete application is hosted locally on your machine and accessed via your browser at http://localhost:8080. This visual layout is called the User Interface (UI). When changes are requested via chat, the agent updates the codebase locally. To see these changes take effect on the frontend, you must manually refresh the browser URL bar.
*   **Web Server & Backend:** To allow your local machine to automatically communicate with remote external platforms like YouTube and TikTok, you must run a local web server in the background. This logical, headless side of the application is called the backend.
*   **API & API Keys:** Your local backend connects to remote servers via an Access Point called an API (Application Programming Interface). Authentication requires a unique API Key. This acts as a highly secure, private password enabling authenticated operations between the two endpoints.
*   **GitHub & Repositories:** GitHub is a cloud platform for codebase management. A Repository (Repo) is a remote project folder where source code is stored. Instead of writing upload algorithms from scratch, this project clones and orchestrates open-source modules (like wkaisertexas/tiktok-uploader) from GitHub to act as the core engine.

---

## Advanced Automation & Automation Layers

*   **TikTok Studio (Web) vs. LIVE Studio:** TikTok LIVE Studio and Live Center are designed for manual, real-time live streaming and cannot be automated for video uploads. For scheduling pre-rendered video clips, this system targets the desktop web interface called TikTok Studio.
*   **Headless Automation (Playwright):** Because the TikTok API is highly restricted for personal accounts, the system utilizes Playwright. Playwright is a background automation engine that acts as an invisible robot—opening a browser instance, navigating pages, inputting text, and clicking upload buttons exactly like a human user.
*   **Session Cookies:** To bypass 2-Factor Authentication (2FA) and Captcha blocks during automated logins, the system imports your active session state via cookies. Cookies act as temporary digital access tokens, verifying your identity to the platform without requiring a password input for every session.

---

## Critical Security Protocol (.gitignore)

*   **The Risk:** Session cookies (`cookies.txt` or `session.json`) and API Keys provide direct, unhindered access to your accounts. If these credentials fall into unauthorized hands, malicious actors can hijack your channels without needing your actual password.
*   **The Shield (.gitignore):** This project uses a strictly defined `.gitignore` file. This configuration file instructs the version control system to completely ignore sensitive files. It ensures your private session cookies, `.env` configs, and API tokens remain localized on your hard drive and are never pushed to public GitHub servers where automated scrapers could harvest them.

---

## Quickstart Implementation Reference

To build this system step-by-step using the Antigravity Agent, open this workspace and feed the following structural prompts to the agent chat:

### Phase 1: Local Server & Dashboard Generation
> "Based on the structural definitions in the README, generate a clean, dark-themed HTML dashboard using Flask serving on localhost:8080. Implement structural controls for TikTok and Instagram toggles, a datetime schedule picker, and a dedicated text-stream block for displaying server logs."

### Phase 2: Filesystem Watching & Core Logic
> "Implement a local directory watcher targeting a specified 'Queue' folder. Upon file detection, pass the filename metadata to the Google Gemini API to generate context-specific descriptions and 3-5 structural hashtags."

### Phase 3: Engine Integration
> "Wire the backend endpoints to the `tiktok-uploader` and `instagrapi` engines. Load authentication states from local cookie files and trigger the publishing process exactly when the scheduled timestamp condition is met. Pipe all standard output logs directly to the dashboard interface."

---

## 1. System Overview

`tiktok-ups` is a centralized orchestrator application designed to automate the lifecycle of short-form video publishing:
- **Directory Ingestion**: Monitors the `./Queue` directory for incoming `.mp4` video assets.
- **AI Copywriting & Tagging**: Integrates Google Gemini API to analyze filename, context, and metadata, generating algorithmically optimized video descriptions and 3-5 structural hashtags.
- **Content Scheduling & Controls**: Web-based minimalist dark-themed dashboard operating at `http://localhost:8080` with platform toggles (TikTok, Instagram) and precise datetime scheduling.
- **Real-Time Log Telemetry**: Streams stdout and orchestrator internal events directly to an embedded browser terminal box via Server-Sent Events (SSE).
- **Multi-Engine Dispatch**: Coordinates background publishing through `tiktok-uploader` (Playwright headless engine) and `instagrapi` using local authentication credentials.

---

## 2. Directory Layout

```
VibeCoding/
├── .venv/                         # Isolated Python virtual environment
├── requirements.txt               # Locked dependencies
├── README.md                      # Orchestrator specification and runbook
├── .env.example                   # Environment configuration template
├── run.py                         # Single-command server & worker launcher
├── Queue/                         # Ingestion directory for new .mp4 files
├── Processed/                     # Archive folder for successfully dispatched assets
├── auth/                          # Authentication cookies and session tokens
│   ├── tiktok_cookies.txt.example
│   └── instagram_session.json.example
└── app/
    ├── __init__.py
    ├── server.py                  # Flask web server (port 8080) & REST/SSE endpoints
    ├── logger.py                  # Stdout interception buffer and SSE broadcaster
    ├── watcher.py                 # Queue directory monitor and trigger pipeline
    ├── gemini_service.py          # Gemini API metadata, copy, and hashtag generator
    ├── scheduler.py               # Time-condition scheduler & dispatcher
    ├── engines/
    │   ├── __init__.py
    │   ├── tiktok_engine.py       # tiktok-uploader execution wrapper
    │   └── instagram_engine.py    # instagrapi Reels/video execution wrapper
    ├── templates/
    │   └── index.html             # Minimalist dark dashboard (strictly zero emojis)
    └── static/
        ├── css/
        │   └── dashboard.css      # Dark theme UI stylesheet
        └── js/
            └── dashboard.js       # UI state management, scheduler sync & SSE logs
```

---

## 3. Environment & Configuration

### Prerequisites
- Python 3.10+ (Python 3.12 verified)
- Playwright browser binaries (`playwright install`)

### Environment Variables (`.env`)
```bash
# Flask Server Configuration
PORT=8080
HOST=127.0.0.1
DEBUG=False

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Engine Credentials Paths
TIKTOK_COOKIES_PATH=auth/tiktok_cookies.txt
INSTAGRAM_SESSION_PATH=auth/instagram_session.json
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

---

## 4. Execution Workflow

1. **Queue Ingestion**:
   - Place any `.mp4` file into `./Queue`.
   - The watcher detects the file, verifies that file write operations have finished, and triggers the processing pipeline.
2. **Metadata & Content Generation**:
   - The video metadata is fed into the Gemini service.
   - Generates an engaging description copy and 3-5 structural hashtags (e.g., `#tech #automation #developer`).
   - The asset is staged in the orchestrator memory / queue overview.
3. **Scheduling & Manual Trigger**:
   - In the dashboard at `http://localhost:8080`, select target platforms (TikTok, Instagram) and the desired publish time.
   - Click "Save Schedule" or click "Dispatch Now" to trigger immediate distribution.
4. **Platform Publishing**:
   - When the scheduled time arrives (or upon manual dispatch), the respective engine handlers are executed in background threads.
   - Full stdout logs and engine events are streamed live to the dashboard terminal.
   - Upon completion, the asset is relocated to `./Processed/`.

---

## 5. Startup Command

Activate the virtual environment and start the orchestrator:

```powershell
.\.venv\Scripts\python.exe run.py
```
Or with activation:
```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```
Access the dashboard at: `http://localhost:8080`
