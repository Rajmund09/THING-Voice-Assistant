# 🗺️ THING Voice Assistant — Master Roadmap & Development Pipeline

> **Version**: 5.1 — OAuth + SDK Edition  
> **Last Updated**: 2026-05-23  
> **Goal**: Evolve THING from a *Power-User Tool* into a *Global-Standard AI Assistant* that surpasses Google Assistant and Amazon Alexa in intelligence, depth, and flexibility.

---

## 📊 Current Architecture Snapshot (v4.0 Baseline)

| Layer | What Exists Today | Status |
|---|---|---|
| **NLU / Routing** | Regex patterns → `intent_router.py` + fuzzy fallback | ✅ Working |
| **LLM Backend** | Groq API (`chat_engine.py`) | ✅ Working |
| **Multi-step Planning** | `action_planner.py` + `intent_priority_router.py` | ✅ Working |
| **Memory** | `context_memory.py` + `memory_engine.py` + `memory.json` | ✅ Working |
| **System Control** | `system_ops.py` — volume, brightness, lock, screenshot | ✅ Working |
| **Web Automation** | Playwright (`browser_ops.py`, `browser_control.py`) | ✅ Working |
| **WhatsApp** | Playwright / URL Scheme (`whatsapp_ops.py`, `number_msg_ops.py`) | ✅ Working |
| **SMS** | System Protocol Handler (`sms_ops.py`) | ✅ Working |
| **YouTube / Media** | `yt-dlp` + keyboard simulation (`youtube_controller.py`) | ✅ Working |
| **Identity / Profiles** | `identity_manager.py`, `profile_manager.py` | ✅ Working |
| **Frontend** | React + Vite + Tailwind (`frontend/`) | ✅ Working |
| **TTS** | `tts_provider.py` + `voice_manager.py` | ✅ Working |
| **Entity Resolution** | `entity_resolver.py` | ✅ Working |

---

## 🛣️ Roadmap Overview

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
  NLU         Vision     Proactive   OAuth+SDK   Mobile+Edge
 Router      & Screen    Observer    Dashboard   Offline AI
(Weeks 1-3) (Weeks 4-6) (Weeks 7-9) (Wks 10-13) (Wks 14-20)
```

---

## 🔵 Phase 1 — Neural NLU: LLM-Driven Intent Router

**Timeline**: Weeks 1–3  
**Priority**: 🔴 CRITICAL — Foundation for all other phases  
**Current State**: `intent_router.py` uses hardcoded regex patterns. Works fast but breaks on any phrasing variation.

### Goal
Replace the regex engine with a **hybrid router**:
1. Regex/fuzzy for speed on clear-cut commands (keep existing layer).
2. LLM-driven structured-output classifier for ambiguous / complex / multi-step commands.

### Architecture

```
User Input
    │
    ▼
[Fast Regex Layer]  ──── hit ────► Execute Action
    │ miss
    ▼
[LLM Intent Classifier]
  Prompt: "Classify this command into one of [INTENTS].
           Extract entities. Return JSON."
    │
    ▼
[Structured Intent JSON]
    │
    ▼
[action_planner.py]  ──► Multi-step Execution
```

### Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `backend/engine/llm_intent_classifier.py` | **NEW** | Calls Groq/Gemini with a system prompt listing all valid intents + entity schemas. Returns structured JSON. |
| `backend/engine/intent_router.py` | **MODIFY** | Add fallback call to `llm_intent_classifier` when regex returns `None`. |
| `backend/engine/intent_priority_router.py` | **MODIFY** | Accept LLM-classified intents in the same format as regex-classified ones. |
| `backend/data/intent_schema.json` | **NEW** | JSON schema of all valid intents + their required entities (used in LLM prompt). |

### Sample LLM Prompt Structure

```python
SYSTEM_PROMPT = """
You are an intent classification engine for a voice assistant.
Given a user command, return a JSON object with:
  - "intent": one of {VALID_INTENTS}
  - "entities": key-value pairs extracted from the command
  - "confidence": float 0-1
  - "multi_step": list of sub-intents if command is compound

If you cannot classify, return {"intent": "unknown", "entities": {}, "confidence": 0}
Return ONLY valid JSON. No explanation.
"""
```

### Acceptance Criteria
- [x] Handles *"If I have any meetings tomorrow, send the details to my manager via WhatsApp and then lock my PC"*
- [x] Handles sarcasm / paraphrasing (e.g., *"crank up the tunes"* → `play_youtube`)
- [x] Falls back gracefully to `chat_engine` if no intent is found
- [x] Contextual Pronoun Resolution (e.g., *"Message Raj hi... now send it to his number"* → resolving 'his')
- [x] Smart Focus Automation (Automated window handling for WhatsApp)
- [x] Latency < 800ms for LLM path, < 20ms for regex path

---

## ✅ Phase 2 — Multimodal Vision: THING Gets Eyes

**Timeline**: Weeks 4–6 — **COMPLETED v4.7**  
**Priority**: 🟠 HIGH  
**Dependency**: Phase 1 (LLM infrastructure required)

### Goal
Integrate **screenshot analysis** using Gemini Vision / GPT-4o so THING can see and interact with any UI element on screen — no API needed.

### Capabilities Unlocked
- *"What does this error message say?"* → reads screen
- *"Summarize this PDF"* → captures document in view
- *"Click the blue Submit button"* → locates and clicks via coordinate mapping
- *"Explain this graph"* → describes visible chart

### Architecture

```
"Describe what's on my screen"
           │
           ▼
    [VisionEngine]
    1. Capture screenshot (mss / pyautogui)
    2. Encode to base64
    3. POST to Gemini Vision API
    4. Parse response
           │
           ▼
    [UIInteractor] (optional)
    - If action needed: PyAutoGUI click at returned coords
```

### Files to Create

| File | Action | Description |
|---|---|---|
| `backend/modules/vision_engine.py` | **NEW** | Captures screen, sends to Gemini Vision, returns description or click coordinates. |
| `backend/modules/ui_interactor.py` | **NEW** | Takes coordinates from VisionEngine and executes clicks/hover via PyAutoGUI. |
| `backend/engine/intent_router.py` | **MODIFY** | Add `vision_query` and `ui_click` intents. |
| `.env.example` | **MODIFY** | Add `GEMINI_API_KEY` entry with documentation. |

### New Dependencies
```
google-generativeai>=0.5.0   # Gemini Vision
mss>=9.0.0                   # Fast multi-monitor screenshot
## 🗺️ PHASE 2: MULTIMODAL VISION & INTERACTION [COMPLETED ✅]
- [x] **Screen Capture Engine**: MSS + PIL for ultra-fast screenshotting.
- [x] **Gemini Vision Integration**: Multi-modal analysis for screen description.
- [x] **UI Interactor**: PyAutoGUI-based safe clicking with coordinate scaling.
- [x] **Hallucination Guard**: Safety gate for visual coordinate validation.
- [x] **Perfection Audit**: Full test suite and production verification.

---

## 🟡 Phase 3 — Proactive Contextual Awareness: THING Thinks Ahead

## 🗺️ PHASE 3: PROACTIVE CONTEXTUAL AWARENESS [COMPLETED ✅]
- [x] **Context Observer**: Background thread monitoring system state.
- [x] **Suggestion Engine**: Logic for intelligent, non-intrusive triggers.
- [x] **Proactive Banner**: Toast-style UI for smart suggestions.
- [x] **Scheduler**: Time-based event triggers (End-of-day, etc.).
- [x] **Advanced Triggers**: Active app monitoring and deep context analysis.
- [x] **Perfection Audit**: Full test suite and production verification.
 7–9  
**Priority**: 🟠 HIGH  
**Dependency**: Phase 1

### Goal
Shift THING from fully **reactive** to partially **proactive**. A background `ContextObserver` thread monitors system state and triggers intelligent suggestions.

### Triggers & Suggestions

| Trigger | Suggested Action |
|---|---|
| Zoom/Teams URL detected in clipboard | *"I see a meeting link. Should I enable Do Not Disturb and open your notes?"* |
| High CPU usage detected | *"Your CPU is at 95%. Want me to close background apps?"* |
| New email from known contact arrives | *"Raj emailed you. Want me to read it?"* |
| System idle for 20 min | *"You've been away. Should I lock your PC?"* |
| Time = 5:00 PM (configurable) | *"End of day! Want me to save open docs and close everything?"* |

### Architecture

```
[ContextObserver Thread] (runs in background every 30s)
    │
    ├── watch_clipboard()    → checks for URLs, meeting links
    ├── watch_processes()    → monitors running apps
    ├── watch_system_load()  → CPU/RAM thresholds
    └── watch_time()         → scheduled event triggers
    │
    ▼
[SuggestionEngine]
    │
    ▼
[Frontend Notification]  ←── WebSocket push to React UI
    │
    ▼
User approves → [action_planner.py] executes
```

### Files to Create

| File | Action | Description |
|---|---|---|
| `backend/core/context_observer.py` | **NEW** | Background thread monitoring clipboard, processes, system load, time. |
| `backend/core/suggestion_engine.py` | **NEW** | Evaluates triggers, generates natural language suggestions. |
| `backend/core/scheduler.py` | **NEW** | Cron-like time-based event trigger system. |
| `frontend/src/components/ProactiveBanner.tsx` | **NEW** | UI component for toast-style suggestion notifications with Accept/Dismiss. |

### New Dependencies
```
psutil>=5.9.0      # CPU/RAM/process monitoring
pyperclip>=1.8.0   # Clipboard monitoring
schedule>=1.2.0    # Time-based scheduling
```

### Acceptance Criteria
- [ ] Zoom link in clipboard triggers DND suggestion within 5 seconds
- [ ] High CPU suggestion appears when usage > 90% for 30+ seconds
- [ ] User can Accept or Dismiss suggestions without interrupting current work
- [ ] Context Observer uses < 0.5% CPU overhead

---

## 🟠 Phase 4 — OAuth Dashboard + Deep SDK Integration

**Timeline**: Weeks 10–13  
**Priority**: 🟡 MEDIUM  
**Dependency**: Phases 1–2

### 4A: OAuth Dashboard

**Goal**: Replace manual `.env` key entry with a settings UI where users click "Connect" for each service.

### Supported OAuth Services

| Service | Auth Method | Capabilities Unlocked |
|---|---|---|
| **Google** | OAuth 2.0 | Calendar, Gmail API, Drive |
| **Spotify** | OAuth 2.0 | Playback control, queue, playlists |
| **Microsoft** | OAuth 2.0 | Outlook, Teams, OneDrive |
| **Slack** | OAuth 2.0 | Send messages, read channels |
| **Notion** | OAuth 2.0 | Read/write pages and databases |

### Architecture

```
[OAuth Dashboard (React)]
    │
    "Connect Google" click
    │
    ▼
[OAuth Flow]
  1. Open browser → Google Auth URL
  2. User grants permissions
  3. Callback URL → backend saves token
    │
    ▼
[Token Store] → backend/data/oauth_tokens.json (encrypted)
    │
    ▼
[Service Module] → uses token for API calls
```

### Files to Create

| File | Action | Description |
|---|---|---|
| `backend/core/oauth_manager.py` | **NEW** | Handles OAuth flows, token refresh, encrypted storage. |
| `backend/modules/google_calendar.py` | **NEW** | Google Calendar read/write via API. |
| `backend/modules/spotify_sdk.py` | **NEW** | Spotify Web API: play, pause, queue, playlists. |
| `backend/modules/slack_sdk_module.py` | **NEW** | Slack API: messages, channel reads. |
| `frontend/src/pages/OAuthDashboard.tsx` | **NEW** | Settings page with service connection cards. |

### 4B: Deep SDK Integration

**Goal**: Replace keyboard simulation with official SDK calls for Spotify, Discord, Slack.

| Current (Simulation) | Target (SDK) |
|---|---|
| Simulate `Space` key to pause YouTube | Spotify SDK: `PUT /me/player/pause` |
| PyAutoGUI to type in Discord | Discord.py: `channel.send(message)` |
| WhatsApp Web Playwright | WhatsApp Business API (optional) |

### New Dependencies
```
spotipy>=2.23.0          # Spotify Web API
slack-sdk>=3.27.0        # Slack API
discord.py>=2.3.0        # Discord API
google-api-python-client # Google APIs
msal>=1.28.0             # Microsoft OAuth
cryptography>=42.0.0     # Token encryption
```

### Acceptance Criteria
- [ ] *"Play my Discover Weekly on Spotify"* works via Spotify SDK (no browser opened)
- [ ] *"Send a message to #general on Slack"* works via Slack API
- [ ] Google Calendar events readable by voice (*"What's my schedule tomorrow?"*)
- [ ] OAuth tokens auto-refresh without user interaction

---

## 🔴 Phase 5 — Edge-AI & Offline Mode

**Timeline**: Weeks 14–20  
**Priority**: 🟡 MEDIUM  
**Dependency**: All previous phases

### Goal
Make core THING functionality work **100% offline** using a local LLM (Llama 3 / Phi-3 via Ollama). Cloud LLMs remain as the "premium" tier.

### Offline Capability Tiers

| Tier | Internet Required | Examples |
|---|---|---|
| **Tier 0: Offline-Always** | ❌ Never | Volume, brightness, lock, scroll, screenshots |
| **Tier 1: Offline-AI** | ❌ Never | Regex + Local LLM intent classification |
| **Tier 2: Online-Preferred** | ✅ Better with | Email, WhatsApp (Playwright still works offline) |
| **Tier 3: Online-Required** | ✅ Always | Web search, YouTube, Spotify SDK, Slack |

### Architecture

```
[THING Runtime]
    │
    ├── Check internet status
    │       │
    │    Online ──► Groq / Gemini API (fast, smart)
    │    Offline ─► Ollama local LLM (Llama 3 / Phi-3)
    │
    ▼
[Capability Filter]
    │
    └── Disable Tier 3 commands when offline
        Show user: "No internet — search unavailable"
```

### Files to Create

| File | Action | Description |
|---|---|---|
| `backend/core/connectivity_monitor.py` | **NEW** | Checks internet availability every 30s, emits events on change. |
| `backend/engine/local_llm_provider.py` | **NEW** | Interfaces with Ollama REST API for local Llama 3 / Phi-3 inference. |
| `backend/core/offline_capability_filter.py` | **NEW** | Disables online-required features and informs user gracefully. |
| `scripts/setup_ollama.sh` | **NEW** | One-command Ollama + model pull setup script. |

### New Dependencies
```
ollama>=0.2.0         # Local LLM runtime client
httpx>=0.27.0         # Already installed — used for Ollama REST calls
```

### Local Model Recommendations

| Model | Size | Best For |
|---|---|---|
| `phi3:mini` | 2.3 GB | Fast intent classification, low-end PCs |
| `llama3:8b` | 4.7 GB | Balanced — good reasoning + speed |
| `llama3:70b` | 40 GB | Near-GPT-4 quality, needs 32GB+ RAM |

### Acceptance Criteria
- [ ] *"Volume up"* works with zero internet connection
- [ ] *"Open Spotify"* works offline (local app launch, no SDK)
- [ ] Seamless fallback: online → offline → online without restart
- [ ] UI shows connectivity status badge (🟢 Online / 🔴 Offline)

---

## 📋 Full Priority Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    THING DEVELOPMENT PIPELINE                           │
│                                                                         │
│  DONE ✅           IN SCOPE 🔵          ROADMAP 🗺️                     
│                                                                         │
│  [Regex NLU]──►[LLM Intent Router]──►[Vision Engine]──►[ProactiveAI]  │
│       │               │                    │                │           │
│  [Groq LLM]      Phase 1 (3wk)        Phase 2 (3wk)   Phase 3 (3wk)  │
│       │                                                                 │
│  [Playwright]──►[OAuth Dashboard]──►[SDK Integration]──►[Offline AI]  │
│  [System Ops]      Phase 4A (2wk)    Phase 4B (2wk)   Phase 5 (7wk)  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

| # | Phase | Weeks | Complexity | Impact | Status |
|---|---|---|---|---|---|
| 1 | LLM Intent Router | 1–3 | 🟡 Medium | 🔴 Critical | ✅ Complete (v4.6) |
| 2 | Vision Engine | 4–6 | 🔴 Hard | 🟠 High | ✅ Complete (v4.7) |
| 3 | Proactive Observer | 7–9 | 🟡 Medium | 🟠 High | ✅ Complete (v5.0) |
| 4A | OAuth Dashboard | 10–11 | 🔴 Hard | 🟡 Medium | ✅ Complete (v5.1) |
| 4B | Deep SDK Integration | 12–13 | 🟡 Medium | 🟡 Medium | ✅ Complete (v5.1) |
| 5 | Edge-AI & Offline | 14–20 | 🔴 Hard | 🟡 Medium | ✅ Complete (v5.5) |

---

## 🧪 Testing Strategy

Each phase must pass the following before being considered complete:

### Unit Tests
- All new modules have corresponding `tests/test_<module>.py` files
- Test both success and graceful failure (no internet, bad API key, etc.)

### Integration Tests
- End-to-end voice command → final action validation
- Multi-step command chains validated (Phase 1 requirement)

### Performance Benchmarks

| Metric | Target |
|---|---|
| Regex intent match latency | < 20ms |
| LLM intent classification latency | < 800ms |
| Vision analysis latency | < 3 seconds |
| Context Observer CPU overhead | < 0.5% |
| Local LLM inference (Phi-3) | < 2 seconds |

---

## 📁 Final Target File Structure

```
THING-Voice-Assistant/
├── backend/
│   ├── core/
│   │   ├── context_observer.py       ← Phase 3 [NEW]
│   │   ├── suggestion_engine.py      ← Phase 3 [NEW]
│   │   ├── scheduler.py              ← Phase 3 [NEW]
│   │   ├── oauth_manager.py          ← Phase 4A [NEW]
│   │   ├── connectivity_monitor.py   ← Phase 5 [NEW]
│   │   └── offline_capability_filter.py ← Phase 5 [NEW]
│   ├── engine/
│   │   ├── intent_router.py          ← Phase 1 [MODIFY]
│   │   ├── llm_intent_classifier.py  ← Phase 1 [NEW]
│   │   ├── intent_priority_router.py ← Phase 1 [MODIFY]
│   │   ├── local_llm_provider.py     ← Phase 5 [NEW]
│   │   └── ... (existing files)
│   ├── modules/
│   │   ├── vision_engine.py          ← Phase 2 [NEW]
│   │   ├── ui_interactor.py          ← Phase 2 [NEW]
│   │   ├── google_calendar.py        ← Phase 4A [NEW]
│   │   ├── spotify_sdk.py            ← Phase 4B [NEW]
│   │   ├── slack_sdk_module.py       ← Phase 4B [NEW]
│   │   └── ... (existing files)
│   └── data/
│       ├── intent_schema.json        ← Phase 1 [NEW]
│       └── oauth_tokens.json         ← Phase 4A [NEW] (gitignored)
├── frontend/
│   └── src/
│       ├── components/
│       │   └── ProactiveBanner.tsx   ← Phase 3 [NEW]
│       └── pages/
│           └── OAuthDashboard.tsx    ← Phase 4A [NEW]
├── scripts/
│   └── setup_ollama.sh              ← Phase 5 [NEW]
├── tests/
│   ├── test_llm_intent_classifier.py ← Phase 1
│   ├── test_vision_engine.py         ← Phase 2
│   ├── test_context_observer.py      ← Phase 3
│   └── test_oauth_manager.py         ← Phase 4A
├── ROADMAP.md                        ← This file
├── THING_vs_Google_Alexa.md
└── README.md
```

---

## 🔖 Version Milestone Targets

| Version | Milestone | Phases Complete |
|---|---|---|
| **v4.0** | Current (Regex NLU + All Modules) | Baseline |
| **v4.5** | ✅ Neural NLU Release | Phase 1 |
| **v4.7** | ✅ Vision-Enabled Release | Phase 1–2 |
| **v5.0** | ✅ Proactive Release | Phase 1–3 |
| **v5.1** | ✅ OAuth + SDK Release | Phase 1–4 |
| **v5.5** | ✅ Supremacy Release (Offline + Edge AI) | Phase 1–5 |

---

*This document is the single source of truth for THING's development direction. Update the status column as phases are completed.*
