#!/usr/bin/env python3
"""
Routine: End-to-end integration test.
Proves the full karaoke pipeline works: song data → lyrics display → grading.
"""

import json
import sys
from pathlib import Path


def run():
    print("=== Routine: End-to-End Integration ===\n")

    song_dir = Path(__file__).parent.parent / "songs" / "love_yourz"
    all_pass = True

    # Test 1: Song data exists and is valid
    print("Test 1: Song data integrity")
    gt_path = song_dir / "ground_truth.json"
    meta_path = song_dir / "metadata.json"
    audio_path = song_dir / "love_yourz.mp3"

    checks = [
        ("ground_truth.json exists", gt_path.exists()),
        ("metadata.json exists", meta_path.exists()),
        ("love_yourz.mp3 exists", audio_path.exists()),
    ]

    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
        if not ok: all_pass = False

    if gt_path.exists():
        gt = json.loads(gt_path.read_text())
        print(f"  ✓ {len(gt['words'])} words, {len(gt['segments'])} segments")

    # Test 2: Frontend serves correctly
    print("\nTest 2: Frontend serves")
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8765/")
        html = resp.read().decode()
        frontend_checks = [
            ("RAPCHECK branding", "RAPCHECK" in html),
            ("Song list component", "song-list" in html),
            ("Lyrics container", "lyrics-container" in html),
            ("Play button", "playBtn" in html),
            ("Grade display", "gradeDisplay" in html),
            ("Mic indicator", "micIndicator" in html),
            ("Countdown overlay", "countdown-overlay" in html),
            ("Word highlighting CSS", ".word.active" in html),
            ("Apple Music scroll", "scroll-behavior" in html),
        ]
        for name, ok in frontend_checks:
            print(f"  {'✓' if ok else '✗'} {name}")
            if not ok: all_pass = False
    except Exception as e:
        print(f"  ✗ Frontend not reachable: {e}")
        all_pass = False

    # Test 3: Song data accessible via HTTP
    print("\nTest 3: Song data accessible via HTTP")
    try:
        resp = urllib.request.urlopen("http://localhost:8765/songs/love_yourz/ground_truth.json")
        data = json.loads(resp.read())
        http_checks = [
            ("Words loaded", len(data.get("words", [])) > 0),
            ("Timestamps valid", all(w["start"] <= w["end"] for w in data.get("words", []))),
            ("Segments loaded", len(data.get("segments", [])) > 0),
        ]
        for name, ok in http_checks:
            print(f"  {'✓' if ok else '✗'} {name}")
            if not ok: all_pass = False
    except Exception as e:
        print(f"  ✗ Could not load song data: {e}")
        all_pass = False

    # Test 4: Grading pipeline works
    print("\nTest 4: Grading pipeline")
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from grade import grade_performance, load_ground_truth

    ground_truth = load_ground_truth(song_dir)
    gt_words = ground_truth["words"]

    # Perfect score
    perfect = grade_performance(gt_words, gt_words)
    grade_checks = [
        ("Perfect score >= 95%", perfect["accuracy_pct"] >= 95),
        ("Perfect grade is S", perfect["grade"] == "S"),
        ("All words correct", perfect["correct_words"] == len(gt_words)),
        ("No misses", perfect["missed_words"] == 0),
    ]
    for name, ok in grade_checks:
        print(f"  {'✓' if ok else '✗'} {name}")
        if not ok: all_pass = False

    # Test 5: Frontend can load song (simulated)
    print("\nTest 5: Frontend-song integration")
    try:
        resp = urllib.request.urlopen("http://localhost:8765/songs/love_yourz/ground_truth.json")
        data = json.loads(resp.read())
        words = data.get("words", [])
        integration_checks = [
            ("530 words match backend", len(words) == 530),
            ("First word is 'Love'", words[0]["word"] == "Love"),
            ("Duration ~193s", 190 < words[-1]["end"] < 200),
        ]
        for name, ok in integration_checks:
            print(f"  {'✓' if ok else '✗'} {name}")
            if not ok: all_pass = False
    except Exception as e:
        print(f"  ✗ Integration check failed: {e}")
        all_pass = False

    print(f"\n{'✓ ALL INTEGRATION TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")
    return all_pass


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
