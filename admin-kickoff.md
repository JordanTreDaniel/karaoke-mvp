# RapCheck Admin Editor — Build Kickoff

## Background
RapCheck is a karaoke grading app at karaoke.jordanchristley.com. Current state: Python server (server.py) + single-file HTML frontend. We're adding an admin editor page at `/admin` using Vite + React + TypeScript + Tailwind CSS.

## Project Location
`/home/jordanc/workspace/karaoke-mvp/`

## Existing Structure
```
server.py              — Python HTTP server (port 8765)
frontend/index.html    — Single-file PoC UI (untouched, stays at /)
songs/<name>/          — Per-song: ground_truth.json, sections.json, metadata.json, audio
```

## Data Format (ground_truth.json)
```json
{
  "text": "Full lyrics text...",
  "segments": [],
  "words": [
    {"word": "Hey", "start": 4.5, "end": 5.06},
    {"word": "look", "start": 5.34, "end": 5.66}
  ]
}
```

## Design Spec
Read: `docs/superpowers/specs/2026-09-26-admin-editor-design.md`

## Working Rules
1. No comments in code
2. No emojis in output
3. TypeScript strict
4. Tailwind CSS (no inline styles except dynamic values)
5. Dark theme: --bg:#0a0a0a, --surface:#141414, --accent:#FF1493, --green:#00E676, --cyan:#00E5FF
6. Inter font family
7. Use `fetch()` with relative URLs (e.g. `/api/songs`)
8. ESM imports

## Task Tree

### Wave 1 — Foundation (parallel)
- [ ] T1: Scaffold Vite+React+Tailwind project in `admin/`
- [ ] T2: Add backend API endpoints to server.py

### Wave 2 — Components + Integration (parallel, depends on Wave 1)
- [ ] T3: SongList component
- [ ] T4: LyricsEditor (Monaco)
- [ ] T5: TimingEditor + WordNode (React Flow)
- [ ] T6: ZoomControls + axis toggle
- [ ] T7: App.tsx with routing + layout
- [ ] T8: api.ts + types.ts

## When Done
- `cd admin && npm run dev` starts the dev server
- `cd admin && npm run build` produces dist/ for production
- Admin loads at /admin/ with song list
- Clicking a song opens editor with Monaco (lyrics) + React Flow (timing)
- Words are draggable/resizable nodes on a time axis
- Zoom in/out works, minimap visible
- Auto-save debounce works
- Existing player at / still works
