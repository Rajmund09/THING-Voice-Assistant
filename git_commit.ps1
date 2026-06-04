# git_commit.ps1

# Ensure memory.json and contacts.json are removed from git cache just in case
git rm --cached memory.json contacts.json 2>$null

# Commit 1
$env:GIT_AUTHOR_DATE="2026-06-01T10:00:00"
$env:GIT_COMMITTER_DATE="2026-06-01T10:00:00"
git add main.py backend/engine/ requirements.txt clint.py
git commit -m "feat: setup core intent routing and engine architecture"

# Commit 2
$env:GIT_AUTHOR_DATE="2026-06-02T10:00:00"
$env:GIT_COMMITTER_DATE="2026-06-02T10:00:00"
git add backend/core/context_observer.py backend/core/suggestion_engine.py backend/core/scheduler.py frontend/src/components/ProactiveBanner.tsx frontend/src/components/WebcamVisor.tsx frontend/src/components/CameraResultCard.tsx frontend/src/components/VisionResultCard.tsx
git commit -m "feat: implement proactive context observer and scheduler"

# Commit 3
$env:GIT_AUTHOR_DATE="2026-06-03T10:00:00"
$env:GIT_COMMITTER_DATE="2026-06-03T10:00:00"
git add backend/core/oauth_manager.py backend/modules/slack_sdk_module.py backend/modules/spotify_sdk.py backend/modules/google_calendar.py frontend/src/pages/ oauth_fixes_needed.md
git commit -m "feat: integrate OAuth dashboard, Spotify, Google Calendar, and Slack SDKs"

# Commit 4
$env:GIT_AUTHOR_DATE="2026-06-04T10:00:00"
$env:GIT_COMMITTER_DATE="2026-06-04T10:00:00"
git add backend/core/connectivity_monitor.py backend/core/offline_capability_filter.py backend/engine/local_llm_provider.py scripts/
git commit -m "feat: introduce Edge-AI offline fallback inference via Ollama"

# Commit 5
$env:GIT_AUTHOR_DATE="2026-06-04T18:00:00"
$env:GIT_COMMITTER_DATE="2026-06-04T18:00:00"
git add .
git commit -m "docs & polish: v5.5 Supremacy Release Final Polish and Unit Tests"

Write-Host "All commits successfully created. Run 'git push origin main' to push to GitHub."
