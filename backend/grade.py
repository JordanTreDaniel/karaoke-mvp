#!/usr/bin/env python3
"""
Karaoke MVP - Grading Pipeline
Takes user recording, runs Whisper, compares against ground truth.
Outputs a grade with accuracy, timing, and flow metrics.
"""

import json
import sys
from pathlib import Path

import whisper


def load_ground_truth(song_dir: Path) -> dict:
    """Load the ground truth timestamps for a song."""
    gt_path = song_dir / "ground_truth.json"
    if not gt_path.exists():
        raise FileNotFoundError(f"No ground truth found at {gt_path}")
    with open(gt_path) as f:
        return json.load(f)


def transcribe_recording(audio_path: Path, song_ground_truth: dict,
                         model_name: str = "base") -> dict:
    """Transcribe user recording with word-level timestamps."""
    print(f"Transcribing recording with Whisper ({model_name})...")

    # Build initial_prompt from ground truth for better AAVE handling
    gt_words = " ".join(w["word"] for w in song_ground_truth.get("words", [])[:50])
    initial_prompt = f"Rap lyrics: {gt_words}"

    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
        initial_prompt=initial_prompt,
    )

    words = []
    for segment in result["segments"]:
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info["word"].strip(),
                "start": round(word_info["start"], 3),
                "end": round(word_info["end"], 3),
            })

    return {
        "text": result["text"],
        "words": words,
        "segments": [
            {"id": s["id"], "start": round(s["start"], 3),
             "end": round(s["end"], 3), "text": s["text"].strip()}
            for s in result["segments"]
        ],
    }


def normalize_word(word: str) -> str:
    """Normalize a word for comparison — lowercase, strip punctuation."""
    import re
    word = word.lower().strip()
    word = re.sub(r'[^\w\s]', '', word)
    return word


def grade_performance(user_words: list, ground_truth_words: list,
                      time_tolerance: float = 0.5) -> dict:
    """
    Grade user performance against ground truth.

    Scoring:
    - Exact match (right word, right time): 10 points
    - Right word, wrong time (within tolerance): 7 points
    - Right word, wrong time (beyond tolerance): 4 points
    - Wrong word: 0 points
    - Flow recovery bonus: +2 points (user fell off then got back on)

    Time tolerance is in seconds — how far off the timing can be.
    """
    if not ground_truth_words:
        return {"error": "No ground truth words"}

    gt_normalized = [{"word": normalize_word(w["word"]), "start": w["start"],
                      "end": w["end"], "idx": i}
                     for i, w in enumerate(ground_truth_words)]

    user_normalized = [{"word": normalize_word(w["word"]), "start": w["start"],
                        "end": w["end"]}
                       for w in user_words]

    results = []
    gt_used = set()
    consecutive_misses = 0
    flow_recoveries = 0

    for u_word in user_normalized:
        best_match = None
        best_score = 0
        best_gt_idx = -1

        for gt in gt_normalized:
            if gt["idx"] in gt_used:
                continue

            if gt["word"] == u_word["word"]:
                time_diff = abs(u_word["start"] - gt["start"])

                if time_diff <= 0.15:
                    score = 10  # Exact timing
                elif time_diff <= time_tolerance:
                    score = 7   # Close enough
                else:
                    score = 4   # Right word, wrong time

                if score > best_score:
                    best_score = score
                    best_match = gt
                    best_gt_idx = gt["idx"]

        if best_match:
            gt_used.add(best_gt_idx)
            consecutive_misses = 0
            results.append({
                "user_word": u_word["word"],
                "expected_word": best_match["word"],
                "score": best_score,
                "timing_diff": round(abs(u_word["start"] - best_match["start"]), 3),
                "status": "correct" if best_score >= 7 else "right_word_wrong_time",
            })
        else:
            consecutive_misses += 1
            results.append({
                "user_word": u_word["word"],
                "expected_word": None,
                "score": 0,
                "timing_diff": None,
                "status": "miss",
            })

            # Detect flow recovery (missed some, then got back on)
            if consecutive_misses >= 2 and len(results) > consecutive_misses:
                next_results = results[len(results):]
                if any(r["score"] >= 7 for r in next_results[:3]):
                    flow_recoveries += 1

    # Calculate totals
    total_possible = len(ground_truth_words) * 10
    total_score = sum(r["score"] for r in results)
    correct_count = sum(1 for r in results if r["status"] == "correct")
    partial_count = sum(1 for r in results if r["status"] == "right_word_wrong_time")
    miss_count = sum(1 for r in results if r["status"] == "miss")

    # Flow recovery bonus
    flow_bonus = flow_recoveries * 2
    total_score += flow_bonus

    accuracy_pct = round((correct_count + partial_count * 0.7) / max(len(ground_truth_words), 1) * 100, 1)
    timing_score = round(correct_count / max(len(results), 1) * 100, 1)

    return {
        "total_score": total_score,
        "max_possible": total_possible + flow_recoveries * 2,
        "accuracy_pct": accuracy_pct,
        "timing_pct": timing_score,
        "correct_words": correct_count,
        "partial_words": partial_count,
        "missed_words": miss_count,
        "total_user_words": len(user_words),
        "total_ground_truth_words": len(ground_truth_words),
        "flow_recoveries": flow_recoveries,
        "grade": _letter_grade(accuracy_pct),
        "word_details": results,
    }


def _letter_grade(pct: float) -> str:
    if pct >= 95: return "S"
    if pct >= 90: return "A"
    if pct >= 80: return "B"
    if pct >= 70: return "C"
    if pct >= 60: return "D"
    return "F"


def grade_song(recording_path: Path, song_name: str,
               model: str = "base") -> dict:
    """Full grading pipeline for a user recording."""
    song_dir = Path(__file__).parent.parent / "songs" / song_name
    if not song_dir.exists():
        raise FileNotFoundError(f"Song directory not found: {song_dir}")

    ground_truth = load_ground_truth(song_dir)
    user_transcription = transcribe_recording(recording_path, ground_truth, model_name=model)
    grade = grade_performance(user_transcription["words"], ground_truth["words"])

    grade["song_name"] = song_name
    grade["user_transcription"] = user_transcription["text"]
    grade["ground_truth_text"] = ground_truth.get("text", "")

    # Save grade
    grade_path = song_dir / f"grade_{recording_path.stem}.json"
    with open(grade_path, "w") as f:
        json.dump(grade, f, indent=2)

    print(f"\n=== GRADE: {grade['grade']} ===")
    print(f"Accuracy: {grade['accuracy_pct']}%")
    print(f"Timing: {grade['timing_pct']}%")
    print(f"Score: {grade['total_score']}/{grade['max_possible']}")
    print(f"Correct: {grade['correct_words']} | Partial: {grade['partial_words']} | Missed: {grade['missed_words']}")
    print(f"Flow recoveries: {grade['flow_recoveries']}")
    print(f"Saved: {grade_path}")

    return grade


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grade a karaoke recording")
    parser.add_argument("recording", help="Path to user recording audio file")
    parser.add_argument("--song", required=True, help="Song name (must match songs/ directory)")
    parser.add_argument("--model", default="base", help="Whisper model size")
    args = parser.parse_args()

    grade_song(Path(args.recording), args.song, args.model)
