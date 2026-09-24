#!/usr/bin/env python3
"""
Routine: Prepare Love Yourz for karaoke MVP
Downloads audio, runs Whisper, saves ground truth.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from prepare_song import prepare_song
from pathlib import Path

LYRICS_PATH = Path(__file__).parent.parent.parent / "rapclouds" / "standalone" / "lyrics" / "love_yourz.txt"

def run():
    print("=== Routine: Prepare Love Yourz ===")
    print(f"Lyrics file: {LYRICS_PATH}")
    print(f"Lyrics exists: {LYRICS_PATH.exists()}")

    if not LYRICS_PATH.exists():
        print("ERROR: Lyrics file not found")
        return False

    metadata = prepare_song(
        youtube_url="https://www.youtube.com/watch?v=6tjlU4w4fSo",
        song_name="love_yourz",
        lyrics_path=str(LYRICS_PATH),
        model="base",
        skip_llm=False,
    )

    # Verify outputs
    song_dir = Path(__file__).parent.parent / "songs" / "love_yourz"
    checks = {
        "audio_file": (song_dir / "love_yourz.mp3").exists(),
        "ground_truth": (song_dir / "ground_truth.json").exists(),
        "whisper_raw": (song_dir / "whisper_raw.json").exists(),
        "metadata": (song_dir / "metadata.json").exists(),
    }

    all_ok = all(checks.values())
    for name, ok in checks.items():
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")

    if all_ok:
        import json
        gt = json.loads((song_dir / "ground_truth.json").read_text())
        print(f"\n  Total words: {len(gt.get('words', []))}")
        print(f"  Total segments: {len(gt.get('segments', []))}")
        if gt.get('words'):
            print(f"  Duration: {gt['words'][-1]['end']:.1f}s")
            print(f"  First 5 words: {[w['word'] for w in gt['words'][:5]]}")

    return all_ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
