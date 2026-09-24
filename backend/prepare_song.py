#!/usr/bin/env python3
"""
Karaoke MVP - Song Preparation Pipeline
Downloads YouTube audio, runs Whisper for word-level timestamps,
corrects against original lyrics via LLM, uploads to R2.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import whisper
import requests

SONGS_DIR = Path(__file__).parent.parent / "songs"
R2_REMOTE = "r2"
R2_BUCKET = "karaoke-mvp"


def download_audio(youtube_url: str, output_path: Path) -> Path:
    """Download audio from YouTube using yt-dlp."""
    # Use content-pipeline venv's yt-dlp (has JS runtime support)
    venv_ytdlp = "/home/jordanc/content-pipeline-venv/bin/yt-dlp"
    if not Path(venv_ytdlp).exists():
        venv_ytdlp = "yt-dlp"  # fallback to system

    cmd = [
        venv_ytdlp,
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--no-playlist",
        "-o", str(output_path) + ".%(ext)s",
        youtube_url,
    ]
    print(f"Downloading audio from {youtube_url}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"yt-dlp stderr: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    # Find the downloaded file (yt-dlp names it based on video title)
    parent = output_path.parent
    mp3_files = sorted(parent.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)
    webm_files = sorted(parent.glob("*.webm"), key=lambda f: f.stat().st_mtime, reverse=True)

    mp3_path = None
    if mp3_files:
        mp3_path = mp3_files[0]
    elif webm_files:
        # Convert webm to mp3
        mp3_path = output_path.with_suffix(".mp3")
        subprocess.run([
            "ffmpeg", "-i", str(webm_files[0]),
            "-codec:a", "libmp3lame", "-q:a", "0",
            str(mp3_path), "-y"
        ], capture_output=True, timeout=60)

    if not mp3_path or not mp3_path.exists():
        # Try the exact name we expected
        mp3_path = output_path.with_suffix(".mp3")
        if not mp3_path.exists():
            raise FileNotFoundError(f"Audio file not found after download in {parent}")

    print(f"Downloaded: {mp3_path} ({mp3_path.stat().st_size / 1024:.1f} KB)")
    return mp3_path


def run_whisper(audio_path: Path, model_name: str = "base") -> dict:
    """Run Whisper with word-level timestamps."""
    print(f"Running Whisper ({model_name} model) with word timestamps...")
    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
        initial_prompt="J. Cole rap lyrics, The Fall Off album",
    )

    # Extract word-level timestamps
    words = []
    for segment in result["segments"]:
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info["word"].strip(),
                "start": round(word_info["start"], 3),
                "end": round(word_info["end"], 3),
            })

    output = {
        "text": result["text"],
        "language": result.get("language", "en"),
        "words": words,
        "segments": [
            {
                "id": s["id"],
                "start": round(s["start"], 3),
                "end": round(s["end"], 3),
                "text": s["text"].strip(),
            }
            for s in result["segments"]
        ],
    }

    print(f"Whisper produced {len(words)} word timestamps across {len(result['segments'])} segments")
    return output


def correct_with_llm(whisper_output: dict, original_lyrics: str, api_key: str) -> dict:
    """Use LLM to correct Whisper output against original lyrics."""
    print("Correcting Whisper output with LLM...")

    whisper_text = whisper_output["text"]
    words_json = json.dumps(whisper_output["words"][:200], indent=2)  # limit for context

    prompt = f"""You are correcting an AI speech-to-text transcription of a rap song against the original lyrics.

ORIGINAL LYRICS:
{original_lyrics}

WHISPER TRANSCRIPTION:
{whisper_text}

WHISPER WORD TIMESTAMPS (first 200 words):
{words_json}

TASK:
1. Compare the Whisper output to the original lyrics
2. Fix any words that were transcribed wrong (common in rap: AAVE, slang, proper nouns)
3. Keep ALL timestamps exactly as-is from Whisper
4. Return a JSON object with this structure:
{{
  "corrected_text": "the full corrected transcription matching original lyrics exactly",
  "corrections": [
    {{"original": "whisper_word", "corrected": "real_word", "reason": "why"}}
  ],
  "words": [
    {{"word": "corrected_word", "start": 0.0, "end": 0.5}}
  ]
}}

IMPORTANT:
- Keep the timestamps from Whisper, only fix the word text
- Match the original lyrics exactly for word choice
- If Whisper got a word right, keep it
- Preserve the flow and order of the original lyrics
- Return ONLY valid JSON, no markdown code blocks"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json={
            "model": "google/gemini-2.0-flash-001",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 4000,
        },
        timeout=60,
    )

    if resp.status_code != 200:
        print(f"LLM API error: {resp.status_code} {resp.text}", file=sys.stderr)
        print("Falling back to raw Whisper output")
        return whisper_output

    content = resp.json()["choices"][0]["message"]["content"]

    # Extract JSON from response
    try:
        # Try direct parse
        corrected = json.loads(content)
    except json.JSONDecodeError:
        # Try extracting from markdown code block
        import re
        match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
        if match:
            corrected = json.loads(match.group(1))
        else:
            print("Could not parse LLM response, using raw Whisper output")
            return whisper_output

    # Merge: keep Whisper timestamps, use corrected words
    if "words" in corrected and len(corrected["words"]) == len(whisper_output["words"]):
        # Direct word replacement
        for i, (orig, new) in enumerate(zip(whisper_output["words"], corrected["words"])):
            orig["word"] = new.get("word", orig["word"])
    elif "words" in corrected:
        # Different count — use corrected words with their timestamps
        whisper_output["words"] = corrected["words"]

    whisper_output["text"] = corrected.get("corrected_text", whisper_output["text"])
    whisper_output["corrections"] = corrected.get("corrections", [])

    print(f"Applied {len(whisper_output.get('corrections', []))} corrections")
    return whisper_output


def upload_to_r2(local_path: Path, remote_name: str) -> str:
    """Upload file to R2 via rclone."""
    remote_path = f"{R2_REMOTE}:{R2_BUCKET}/{remote_name}"
    cmd = ["rclone", "copy", str(local_path), remote_path, "--progress"]
    print(f"Uploading to R2: {remote_path}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"R2 upload warning: {result.stderr}", file=sys.stderr)
    return remote_path


def prepare_song(youtube_url: str, song_name: str, lyrics_path: str = None,
                 model: str = "base", skip_llm: bool = False) -> dict:
    """Full pipeline: download → whisper → correct → save."""
    song_dir = SONGS_DIR / song_name
    song_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download audio
    audio_path = song_dir / f"{song_name}"
    audio_file = download_audio(youtube_url, audio_path)

    # 2. Run Whisper
    whisper_result = run_whisper(audio_file, model_name=model)

    # Save raw whisper output
    raw_path = song_dir / "whisper_raw.json"
    with open(raw_path, "w") as f:
        json.dump(whisper_result, f, indent=2)
    print(f"Raw Whisper output saved: {raw_path}")

    # 3. Correct with LLM (unless skipped)
    if not skip_llm:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if api_key and lyrics_path:
            original_lyrics = Path(lyrics_path).read_text()
            whisper_result = correct_with_llm(whisper_result, original_lyrics, api_key)
        else:
            if not api_key:
                print("No OPENROUTER_API_KEY found, skipping LLM correction")
            if not lyrics_path:
                print("No lyrics file provided, skipping LLM correction")

    # 4. Save corrected output
    corrected_path = song_dir / "ground_truth.json"
    with open(corrected_path, "w") as f:
        json.dump(whisper_result, f, indent=2)
    print(f"Ground truth saved: {corrected_path}")

    # 5. Upload audio to R2
    try:
        upload_to_r2(audio_file, f"{song_name}/{audio_file.name}")
    except Exception as e:
        print(f"R2 upload failed (non-fatal): {e}")

    # 6. Create metadata
    metadata = {
        "song_name": song_name,
        "youtube_url": youtube_url,
        "lyrics_file": lyrics_path,
        "audio_file": str(audio_file.name),
        "whisper_model": model,
        "total_words": len(whisper_result.get("words", [])),
        "total_segments": len(whisper_result.get("segments", [])),
        "duration_seconds": whisper_result["words"][-1]["end"] if whisper_result.get("words") else 0,
    }
    meta_path = song_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n=== Song prepared: {song_name} ===")
    print(f"Audio: {audio_file}")
    print(f"Words: {metadata['total_words']}")
    print(f"Duration: {metadata['duration_seconds']:.1f}s")
    print(f"Ground truth: {corrected_path}")

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare a song for karaoke")
    parser.add_argument("youtube_url", help="YouTube URL of the song")
    parser.add_argument("--name", required=True, help="Song identifier (e.g., love_yourz)")
    parser.add_argument("--lyrics", help="Path to original lyrics .txt file")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper model size (default: base)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM correction")
    args = parser.parse_args()

    prepare_song(
        youtube_url=args.youtube_url,
        song_name=args.name,
        lyrics_path=args.lyrics,
        model=args.model,
        skip_llm=args.skip_llm,
    )
