#!/usr/bin/env python3
"""
Routine: Verify ground truth data integrity.
Checks that Whisper output has valid timestamps and word alignment.
"""

import json
import sys
from pathlib import Path


def run():
    print("=== Routine: Verify Ground Truth ===")

    gt_path = Path(__file__).parent.parent / "songs" / "love_yourz" / "ground_truth.json"
    if not gt_path.exists():
        print(f"  ✗ Ground truth not found: {gt_path}")
        return False

    gt = json.loads(gt_path.read_text())

    checks = []

    # Check words exist
    words = gt.get("words", [])
    checks.append(("Words exist", len(words) > 0, f"{len(words)} words"))

    # Check timestamps are monotonically increasing
    timestamps_ok = all(
        words[i]["start"] <= words[i]["end"]
        for i in range(len(words))
    )
    checks.append(("Timestamps valid", timestamps_ok, "start <= end for all words"))

    # Check monotonic ordering (with tolerance for overlapping words)
    monotonic = all(
        words[i]["start"] <= words[i+1]["start"]
        for i in range(len(words)-1)
    )
    checks.append(("Monotonic ordering", monotonic, "words ordered by start time"))

    # Check segments exist
    segments = gt.get("segments", [])
    checks.append(("Segments exist", len(segments) > 0, f"{len(segments)} segments"))

    # Check duration is reasonable (Love Yourz is ~3:30)
    if words:
        duration = words[-1]["end"]
        reasonable = 150 < duration < 300  # 2.5-5 minutes
        checks.append(("Duration reasonable", reasonable, f"{duration:.1f}s"))

    # Check word content is non-empty
    non_empty = all(w["word"].strip() for w in words)
    checks.append(("No empty words", non_empty, ""))

    # Print results
    all_ok = True
    for name, ok, detail in checks:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}" + (f" ({detail})" if detail else ""))
        if not ok:
            all_ok = False

    # Show first/last few words
    if words:
        print(f"\n  First 5 words: {[(w['word'], w['start']) for w in words[:5]]}")
        print(f"  Last 5 words: {[(w['word'], w['start']) for w in words[-5:]]}")

    # Show sample segment
    if segments:
        s = segments[0]
        print(f"\n  First segment: [{s['start']:.1f}-{s['end']:.1f}] {s['text'][:60]}...")

    # Check corrections were applied
    corrections = gt.get("corrections", [])
    if corrections:
        print(f"\n  LLM corrections applied: {len(corrections)}")
        for c in corrections[:5]:
            print(f"    '{c['original']}' → '{c['corrected']}' ({c.get('reason', '')})")

    return all_ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
