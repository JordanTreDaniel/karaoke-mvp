# RapCheck Admin Editor — Design Spec

## Overview
Admin page for editing song lyrics and word timing in the RapCheck karaoke app. Lives at `/admin` alongside the existing player at `/`.

## Architecture
- **Frontend**: Vite + React 18 + TypeScript + Tailwind CSS
- **Backend**: Existing Python server (`server.py`) with new API endpoints
- **Editor**: Monaco for lyrics text, React Flow for timing canvas

## Components

### SongList
- Fetches `GET /api/songs`, displays song cards (name, word count, duration)
- Click to open editor for that song

### LyricsEditor
- Monaco editor loaded with `ground_truth.json` text field
- Auto-saves on change with 1s debounce via `PUT /api/songs/<name>/text`
- Shows word count and duration stats

### TimingEditor (React Flow)
- Each word = custom React Flow node showing the word text
- Linear layout along time axis (default: X-axis = time)
- Axis toggle: time on X or Y
- Draggable nodes to adjust word start time
- Resizable nodes where width/height = word duration
- Built-in zoom + minimap from React Flow
- Navigation scrubber bar (always fits on screen)
- Changes auto-save via `PUT /api/songs/<name>/timing`

### WordNode (custom React Flow node)
- Displays word text inside a rounded rect
- Color indicates timing status (default, adjusted, conflict)
- Drag handle for repositioning
- Resize handle for duration adjustment

## Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/songs` | GET | List all songs with metadata |
| `/api/songs/<name>` | GET | Get full ground_truth.json |
| `/api/songs/<name>/text` | PUT | Update lyrics text, regenerate word objects |
| `/api/songs/<name>/timing` | PUT | Update word timings |
| `/api/songs/<name>/recalc` | POST | Re-run Whisper to regenerate timings |

## File Structure
```
admin/
  src/
    App.tsx
    main.tsx
    index.css (Tailwind)
    components/
      SongList.tsx
      LyricsEditor.tsx
      TimingEditor.tsx
      WordNode.tsx
      ZoomControls.tsx
    api.ts
    types.ts
  index.html
  package.json
  vite.config.ts
  tailwind.config.js
  postcss.config.js
  tsconfig.json
```

## Data Model
```typescript
interface Word {
  word: string;
  start: number;  // seconds
  end: number;    // seconds
}

interface GroundTruth {
  text: string;
  segments: any[];
  words: Word[];
}

interface SongMeta {
  name: string;
  audio: string;
  words: number;
  duration: number;
  youtube_url: string;
}
```

## Styling
- Dark theme matching existing app (--bg: #0a0a0a, --accent: #FF1493)
- Tailwind CSS with custom theme tokens
- Inter font family

## Constraints
- Existing player at `/` untouched
- Admin at `/admin/` served from `admin/dist/`
- Auto-save with 1s debounce (no explicit save button)
- No new dependencies beyond Vite, React, Monaco, React Flow, Tailwind
