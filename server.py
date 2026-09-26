#!/usr/bin/env python3
"""
RapCheck — Karaoke MVP Server
Uses OpenAI Whisper API for fast transcription.
Serves frontend, handles song prep, grades recordings.
"""

import base64
import http.server
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import wave
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
SONGS_DIR = BASE_DIR / "songs"
FRONTEND_DIR = BASE_DIR / "frontend"
ADMIN_DIR = BASE_DIR / "admin" / "dist"
PORT = 8765

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
WHISPER_API = "https://api.openai.com/v1/audio/transcriptions"


def openai_transcribe(audio_path: str, prompt: str = "") -> dict:
    """Transcribe audio using OpenAI Whisper API (fast, ~2-5s)."""
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}

    with open(audio_path, "rb") as f:
        files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
        data = {
            "model": "whisper-1",
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word",
            "language": "en",
        }
        if prompt:
            data["prompt"] = prompt

        resp = requests.post(WHISPER_API, headers=headers, files=files, data=data, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"Whisper API error {resp.status_code}: {resp.text[:300]}")

    return resp.json()


def prepare_song(youtube_url: str, song_name: str, lyrics_text: str = None):
    """Download + transcribe a song."""
    song_dir = SONGS_DIR / song_name
    song_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download audio
    audio_path = song_dir / f"{song_name}.mp3"
    if not audio_path.exists():
        ytdlp = "/home/jordanc/content-pipeline-venv/bin/yt-dlp"
        cmd = [
            ytdlp, "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "0", "--no-playlist",
            "-o", str(song_dir / f"{song_name}.%(ext)s"),
            youtube_url,
        ]
        print(f"Downloading {youtube_url}...")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return {"error": f"yt-dlp failed: {r.stderr[:300]}"}

    mp3s = list(song_dir.glob("*.mp3"))
    if not mp3s:
        return {"error": "No mp3 found after download"}
    audio_path = mp3s[0]

    # 2. Convert to 16kHz mono WAV for Whisper API
    wav_path = song_dir / f"{song_name}.wav"
    if not wav_path.exists():
        subprocess.run([
            "ffmpeg", "-i", str(audio_path),
            "-ar", "16000", "-ac", "1",
            str(wav_path), "-y"
        ], capture_output=True, timeout=60)

    # 3. Transcribe via OpenAI Whisper API
    print(f"Transcribing {audio_path.name} via OpenAI Whisper API...")
    result = openai_transcribe(str(wav_path))

    # 4. Extract word-level timestamps (filter emoji and non-word tokens)
    words = []
    for w in result.get("words", []):
        word_text = w["word"].strip()
        # Skip emoji, musical symbols, and non-word tokens
        if not word_text or any(ord(c) > 0xFFFF for c in word_text):
            continue
        words.append({
            "word": word_text,
            "start": round(w["start"], 3),
            "end": round(w["end"], 3),
        })

    # 5. Extract segments
    segments = []
    for s in result.get("segments", []):
        segments.append({
            "id": s["id"],
            "start": round(s["start"], 3),
            "end": round(s["end"], 3),
            "text": s["text"].strip(),
        })

    ground_truth = {
        "text": result.get("text", ""),
        "words": words,
        "segments": segments,
    }

    # 6. Save
    (song_dir / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2))
    duration = words[-1]["end"] if words else 0
    meta = {
        "name": song_name,
        "audio": audio_path.name,
        "words": len(words),
        "segments": len(segments),
        "duration": duration,
        "youtube_url": youtube_url,
    }
    (song_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

    # 7. Detect sections via LLM
    sections = detect_sections_llm(words, result.get("text", ""))
    if sections:
        (song_dir / "sections.json").write_text(json.dumps(sections, indent=2))
        print(f"Sections: {len(sections)} sections saved")

    print(f"Done: {len(words)} words, {duration:.0f}s")
    return meta


def normalize(w):
    import re
    return re.sub(r'[^\w]', '', w.lower().strip())


def detect_sections_llm(words, full_text):
    """Use OpenAI to label song sections (intro/verse/chorus/bridge/outro)."""
    if not OPENAI_KEY or not words:
        return []

    # Build a compact representation: group words into ~10s chunks with timestamps
    chunks = []
    chunk_start = words[0]["start"]
    chunk_words = []
    for w in words:
        chunk_words.append(w["word"])
        if w["end"] - chunk_start >= 10 or w == words[-1]:
            chunks.append({
                "t": f"{chunk_start:.0f}-{w['end']:.0f}",
                "text": " ".join(chunk_words),
            })
            chunk_start = w["end"]
            chunk_words = []

    chunks_json = json.dumps(chunks, indent=1)

    prompt = f"""Analyze this song and divide it into sections (intro, verse, chorus, bridge, outro).

LYRICS:
{full_text}

TIMED CHUNKS (start_end: words):
{chunks_json}

Return a JSON array of section objects. Each section covers one or more consecutive chunks.
Use ONLY these labels: "intro", "verse", "chorus", "bridge", "outro".

Return ONLY valid JSON array, no markdown:
[{{"label": "intro", "start": 0.0, "end": 22.0}}, {{"label": "verse", "start": 22.0, "end": 65.0}}, ...]

Rules:
- intro: short opening before first verse (instrumental, ad-libs, repeated hook)
- verse: main lyrical content (rap verses, storytelling)
- chorus: repeated section with the hook/refrain
- bridge: contrasting section between verses/chorus
- outro: closing section (repeated hook, fade-out, ad-libs)
- start/end must be in seconds, matching the chunk timestamps
- cover the ENTIRE song from first chunk to last"""

    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 2000},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"LLM section detection failed: {resp.status_code}")
            return []
        content = resp.json()["choices"][0]["message"]["content"]
        # Parse JSON (handle markdown code blocks)
        import re
        match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
        text = match.group(1) if match else content.strip()
        sections = json.loads(text)
        print(f"LLM detected {len(sections)} sections")
        return sections
    except Exception as e:
        print(f"Section detection error: {e}")
        return []


def find_best_segments(gt_words, clip_seconds=15):
    """Find the best 15-second segments to practice (densest lyrics)."""
    if not gt_words:
        return []

    duration = gt_words[-1]["end"]
    step = 5  # slide window by 5s
    candidates = []

    for start_t in range(0, int(duration) - clip_seconds, step):
        end_t = start_t + clip_seconds
        words_in_clip = [w for w in gt_words if w["start"] >= start_t and w["end"] <= end_t]
        if len(words_in_clip) >= 5:  # at least 5 words to be interesting
            candidates.append({
                "start": start_t,
                "end": end_t,
                "word_count": len(words_in_clip),
                "preview": " ".join(w["word"] for w in words_in_clip[:8]) + "...",
            })

    # Sort chronologically (not by density — density scrambles the song order)
    candidates.sort(key=lambda c: c["start"])
    return candidates


def grade_recording(recording_path: str, song_name: str, clip_start: float = None, clip_end: float = None):
    """Grade a user recording against ground truth."""
    song_dir = SONGS_DIR / song_name
    gt_path = song_dir / "ground_truth.json"
    if not gt_path.exists():
        return {"error": "No ground truth for this song"}

    gt = json.loads(gt_path.read_text())
    gt_words = gt["words"]

    # If clip specified, filter ground truth to that segment
    if clip_start is not None and clip_end is not None:
        gt_words = [w for w in gt_words if w["start"] >= clip_start and w["end"] <= clip_end]
        if not gt_words:
            return {"error": "No words in selected clip"}

    # Transcribe user recording via OpenAI Whisper API
    # Don't inject expected words — biases the transcription
    prompt = "rap lyrics, music performance"
    print(f"Grading recording via OpenAI Whisper API...")
    result = openai_transcribe(recording_path, prompt)

    user_words = []
    # what does this for loop do? feel sus
    for w in result.get("words", []):
        user_words.append({
            "word": w["word"].strip(),
            "start": round(w["start"], 3),
            "end": round(w["end"], 3),
        })

    if not user_words:
        return {"error": "No words detected in recording", "grade": "F",
                "accuracy": 0, "timing": 0, "score": 0, "max": len(gt_words) * 10,
                "correct": 0, "partial": 0, "missed": 0, "total_words": len(gt_words),
                "user_words": 0, "flow_recoveries": 0, "details": [],
                "segments": find_best_segments(gt["words"])}

    # Align timestamps: shift ground truth to match recording start
    gt_first = gt_words[0]["start"]
    user_first = user_words[0]["start"]
    offset = user_first - gt_first

    gt_norm = []
    for i, w in enumerate(gt_words):
        gt_norm.append({
            "norm": normalize(w["word"]),
            "start": w["start"] + offset,
            "end": w["end"] + offset,
            "i": i,
        })

    # Grade word-by-word
    results = []
    gt_used = set()
    consecutive_misses = 0
    flow_recoveries = 0

    # TODO: should we loop over the user words, time, or gt words when grading?
    for uw in user_words:
        un = normalize(uw["word"])
        best = None
        best_score = 0

        for g in gt_norm:
            if g["i"] in gt_used:
                continue
            if g["norm"] == un:
                tdiff = abs(uw["start"] - g["start"])
                if tdiff <= 0.15:
                    score = 10
                elif tdiff <= 0.8:
                    score = 7
                else:
                    score = 4
                # what makes a score a "best"?
                if score > best_score:
                    best_score = score
                    best = g

        if best:
            gt_used.add(best["i"]) # wtf is this?
            consecutive_misses = 0
            results.append({
                "word": uw["word"],
                "expected": gt_words[best["i"]]["word"],
                "score": best_score,
                "diff": round(abs(uw["start"] - best["start"]), 3),
                "status": "correct" if best_score >= 7 else "late",
            })
        else:
            consecutive_misses += 1
            results.append({
                "word": uw["word"], "expected": None,
                "score": 0, "diff": None, "status": "miss",
            })

    # Flow recovery: detect miss→miss→correct patterns (post-processing)
    consecutive_misses = 0
    for r in results:
        if r["status"] == "miss":
            consecutive_misses += 1
        else:
            if consecutive_misses >= 2 and r["score"] >= 7:
                flow_recoveries += 1
            consecutive_misses = 0

    correct = sum(1 for r in results if r["status"] == "correct")
    partial = sum(1 for r in results if r["status"] == "late")
    missed = sum(1 for r in results if r["status"] == "miss")
    total_attempted = len(results)  # words user actually sang
    total_gt = len(gt_words)       # words expected in clip

    # Accuracy: how many of the user's words were correct (not penalized for skipping)
    accuracy = round((correct + partial * 0.7) / max(total_attempted, 1) * 100, 1)
    # Timing: what % of matched words had good timing
    timing = round(correct / max(correct + partial, 1) * 100, 1)
    # Score: points earned vs points possible for attempted words
    score = sum(r["score"] for r in results) + flow_recoveries * 2
    max_possible = total_attempted * 10 + flow_recoveries * 2

    if accuracy >= 95: letter = "S"
    elif accuracy >= 90: letter = "A"
    elif accuracy >= 80: letter = "B"
    elif accuracy >= 70: letter = "C"
    elif accuracy >= 60: letter = "D"
    else: letter = "F"

    # Include suggested segments for next try
    segments = find_best_segments(gt["words"])

    return {
        "grade": letter, "accuracy": accuracy, "timing": timing,
        "score": score, "max": max_possible,
        "correct": correct, "partial": partial, "missed": missed,
        "total_words": total_gt, "total_attempted": total_attempted,
        "user_words": len(user_words), "flow_recoveries": flow_recoveries,
        "details": results,
        "segments": segments,
    }


# ─── HTTP Server ────────────────────────────────────────────────────

class RapCheckHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        # Read body in chunks for large payloads (base64 audio)
        raw = b""
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            raw += chunk
            remaining -= len(chunk)
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            self.send_json(400, {"error": f"Bad JSON: {e}"})
            return

        if self.path == "/api/prepare":
            name = body.get("name", "custom")
            url = body.get("url", "")
            lyrics = body.get("lyrics", "")
            if not url:
                self.send_json(400, {"error": "url required"})
                return
            result = prepare_song(url, name, lyrics)
            self.send_json(200, result)

        elif self.path == "/api/grade":
            song = body.get("song", "")
            clip_start = body.get("clip_start")
            clip_end = body.get("clip_end")
            audio_b64 = body.get("audio", "")
            if not audio_b64 or not song:
                self.send_json(400, {"error": "song and audio required"})
                return

            # Timestamp for this recording
            ts = time.strftime("%Y%m%d_%H%M%S")

            # Save recording locally and to R2
            recording_dir = SONGS_DIR / song / "recordings"
            recording_dir.mkdir(parents=True, exist_ok=True)
            recording_path = recording_dir / f"{ts}.webm"
            recording_path.write_bytes(base64.b64decode(audio_b64))

            # Convert to 16kHz mono WAV for Whisper API
            tmp = str(recording_path)
            wav = tmp.replace(".webm", ".wav")
            try:
                subprocess.run(
                    ["ffmpeg", "-i", tmp, "-ar", "16000", "-ac", "1", wav, "-y"],
                    capture_output=True, timeout=30,
                )
                result = grade_recording(wav, song, clip_start, clip_end)

                # Add metadata to result
                result["song"] = song
                result["timestamp"] = ts
                result["clip_start"] = clip_start
                result["clip_end"] = clip_end

                # Save grade locally
                grade_dir = SONGS_DIR / song / "grades"
                grade_dir.mkdir(parents=True, exist_ok=True)
                grade_path = grade_dir / f"{ts}.json"
                grade_path.write_text(json.dumps(result, indent=2))

                # Upload to R2 in background (non-blocking)
                try:
                    subprocess.Popen([
                        "rclone", "copy", str(recording_path),
                        f"r2:karaoke-poc/recordings/{song}/{ts}.webm",
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.Popen([
                        "rclone", "copy", str(grade_path),
                        f"r2:karaoke-poc/grades/{song}/{ts}.json",
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass  # R2 upload is non-critical

                self.send_json(200, result)
            finally:
                for p in [wav]:
                    if os.path.exists(p):
                        os.unlink(p)

        elif self.path == "/api/songs":
            songs = []
            for d in sorted(SONGS_DIR.iterdir()):
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    songs.append(json.loads(meta_path.read_text()))
            self.send_json(200, songs)

        elif self.path.startswith("/api/songs/") and self.path.endswith("/recalc"):
            song_name = self.path[len("/api/songs/"):-len("/recalc")]
            song_dir = SONGS_DIR / song_name
            gt_path = song_dir / "ground_truth.json"
            if not gt_path.exists():
                self.send_json(404, {"error": "song not found"})
                return
            self.send_json(200, {"status": "not_implemented"})
            return

        else:
            self.send_json(404, {"error": "not found"})

    def do_GET(self):
        if self.path == "/api/songs":
            songs = []
            for d in sorted(SONGS_DIR.iterdir()):
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    songs.append(json.loads(meta_path.read_text()))
            self.send_json(200, songs)
            return

        if self.path.startswith("/api/songs/"):
            song_name = self.path[len("/api/songs/"):]
            song_dir = SONGS_DIR / song_name
            gt_path = song_dir / "ground_truth.json"
            if gt_path.exists():
                gt = json.loads(gt_path.read_text())
                self.send_json(200, gt)
            else:
                self.send_json(404, {"error": "song not found"})
            return

        if self.path.startswith("/songs/"):
            song_path = SONGS_DIR / self.path[7:]
            if song_path.exists() and song_path.is_file():
                self.send_file(song_path)
                return

        if self.path.startswith("/admin"):
            admin_path = self.path[len("/admin"):] or "/"
            if admin_path == "/":
                admin_path = "/index.html"
            file_path = ADMIN_DIR / admin_path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self.send_file(file_path)
                return
            index_path = ADMIN_DIR / "index.html"
            if index_path.exists():
                self.send_file(index_path)
                return

        super().do_GET()

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = b""
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            raw += chunk
            remaining -= len(chunk)
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            self.send_json(400, {"error": f"Bad JSON: {e}"})
            return

        if self.path.endswith("/text") and self.path.startswith("/api/songs/"):
            song_name = self.path[len("/api/songs/"):-len("/text")]
            song_dir = SONGS_DIR / song_name
            gt_path = song_dir / "ground_truth.json"
            if not gt_path.exists():
                self.send_json(404, {"error": "song not found"})
                return
            gt = json.loads(gt_path.read_text())
            gt["text"] = body.get("text", gt.get("text", ""))
            gt_path.write_text(json.dumps(gt, indent=2))
            self.send_json(200, {"status": "updated"})
            return

        if self.path.endswith("/timing") and self.path.startswith("/api/songs/"):
            song_name = self.path[len("/api/songs/"):-len("/timing")]
            song_dir = SONGS_DIR / song_name
            gt_path = song_dir / "ground_truth.json"
            if not gt_path.exists():
                self.send_json(404, {"error": "song not found"})
                return
            gt = json.loads(gt_path.read_text())
            gt["words"] = body.get("words", gt.get("words", []))
            gt_path.write_text(json.dumps(gt, indent=2))
            self.send_json(200, {"status": "updated"})
            return

        self.send_json(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        data = path.read_bytes()
        ct = "application/octet-stream"
        if path.suffix == ".mp3": ct = "audio/mpeg"
        elif path.suffix == ".json": ct = "application/json"
        elif path.suffix == ".wav": ct = "audio/wav"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        if "/songs/" not in str(args):
            super().log_message(format, *args)


def main():
    if not OPENAI_KEY:
        print("WARNING: No OPENAI_API_KEY found. Grading will fail.")

    # Pre-prepare Love Yourz if not done
    love_dir = SONGS_DIR / "love_yourz"
    if not (love_dir / "ground_truth.json").exists():
        lyrics = Path("/home/jordanc/workspace/rapclouds/standalone/lyrics/love_yourz.txt")
        if lyrics.exists():
            print("Preparing Love Yourz...")
            prepare_song(
                "https://www.youtube.com/watch?v=6tjlU4w4fSo",
                "love_yourz",
                lyrics.read_text(),
            )
    else:
        print("Love Yourz already prepared.")

    print(f"\nRapCheck running at http://localhost:{PORT}")
    server = http.server.HTTPServer(("0.0.0.0", PORT), RapCheckHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
