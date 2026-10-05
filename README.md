> ⚠️ **DEPRECATED** — superseded by the karaoke implementation in JordanTreDaniel/rapclouds (karaoke tab). Kept for historical purposes only.

# RapCheck — Karaoke MVP

Proof of concept: pick a song section, rap it, get graded word-by-word.

## Stack
- **Backend:** Python stdlib HTTP server + OpenAI Whisper API + ffmpeg
- **Frontend:** Single HTML file (no build step)
- **Grading:** Whisper transcribes your recording, compares word-for-word against ground truth timestamps

## Run
```bash
cd ~/workspace/karaoke-mvp
export OPENAI_API_KEY=sk-...
python3.10 server.py
# http://localhost:8765
```

## Adding Songs
```bash
python3.10 -c "
from server import prepare_song
prepare_song('YOUTUBE_URL', 'song_name')
"
```
Place clean lyrics at `rapclouds/standalone/lyrics/song_name.txt` for future alignment.

## Live
https://karaoke.jordanchristley.com

## Status
PoC — HTML frontend, no auth, single-user. Will be rebuilt as proper React app.
