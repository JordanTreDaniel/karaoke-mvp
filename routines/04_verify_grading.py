#!/usr/bin/env python3
"""
Routine: Verify grading pipeline.
Uses the original song audio as a "perfect performance" to test grading.
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from grade import grade_performance, load_ground_truth


def run():
    print("=== Routine: Verify Grading Pipeline ===")

    song_dir = Path(__file__).parent.parent / "songs" / "love_yourz"
    if not (song_dir / "ground_truth.json").exists():
        print("  ✗ No ground truth found. Run 01_prepare_song.py first.")
        return False

    ground_truth = load_ground_truth(song_dir)
    gt_words = ground_truth.get("words", [])

    # Test 1: Perfect performance (same timestamps)
    print("\n  Test 1: Perfect performance (identical words/timing)")
    perfect_grade = grade_performance(gt_words, gt_words)
    print(f"    Grade: {perfect_grade['grade']}")
    print(f"    Accuracy: {perfect_grade['accuracy_pct']}%")
    print(f"    Correct: {perfect_grade['correct_words']}, Missed: {perfect_grade['missed_words']}")

    test1_ok = perfect_grade["accuracy_pct"] >= 95
    print(f"    {'✓' if test1_ok else '✗'} Perfect performance grades >= 95%")

    # Test 2: Late performance (same words, 0.5s late)
    print("\n  Test 2: Late performance (0.5s behind)")
    late_words = [
        {"word": w["word"], "start": w["start"] + 0.5, "end": w["end"] + 0.5}
        for w in gt_words
    ]
    late_grade = grade_performance(late_words, gt_words, time_tolerance=1.0)
    print(f"    Grade: {late_grade['grade']}")
    print(f"    Accuracy: {late_grade['accuracy_pct']}%")
    print(f"    Correct: {late_grade['correct_words']}, Partial: {late_grade['partial_words']}")

    test2_ok = late_grade["accuracy_pct"] >= 60 and late_grade["partial_words"] > 0
    print(f"    {'✓' if test2_ok else '✗'} Late performance gets partial credit")

    # Test 3: Partial performance (skip every 3rd word)
    print("\n  Test 3: Partial performance (skip every 3rd word)")
    partial_words = [w for i, w in enumerate(gt_words) if i % 3 != 0]
    partial_grade = grade_performance(partial_words, gt_words)
    print(f"    Grade: {partial_grade['grade']}")
    print(f"    Accuracy: {partial_grade['accuracy_pct']}%")
    print(f"    Total user words: {partial_words.__len__()}, GT words: {len(gt_words)}")

    test3_ok = 40 <= partial_grade["accuracy_pct"] <= 80
    print(f"    {'✓' if test3_ok else '✗'} Partial performance grades in 40-80% range")

    # Test 4: Wrong words (different lyrics entirely)
    print("\n  Test 4: Wrong lyrics (different song)")
    wrong_words = [{"word": f"fake_{i}", "start": w["start"], "end": w["end"]}
                   for i, w in enumerate(gt_words)]
    wrong_grade = grade_performance(wrong_words, gt_words)
    print(f"    Grade: {wrong_grade['grade']}")
    print(f"    Accuracy: {wrong_grade['accuracy_pct']}%")
    print(f"    Missed: {wrong_grade['missed_words']}")

    test4_ok = wrong_grade["accuracy_pct"] < 10
    print(f"    {'✓' if test4_ok else '✗'} Wrong lyrics grade < 10%")

    all_ok = test1_ok and test2_ok and test3_ok and test4_ok
    print(f"\n  {'✓ ALL TESTS PASSED' if all_ok else '✗ SOME TESTS FAILED'}")
    return all_ok


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
