#!/usr/bin/env python3
"""Run LLM correction on Whisper output."""
import os, json, requests, re
from pathlib import Path

api_key = os.environ.get('OPENROUTER_API_KEY', '')
if not api_key:
    print("No OPENROUTER_API_KEY")
    exit(1)

gt_path = Path(__file__).parent.parent / 'songs' / 'love_yourz' / 'whisper_raw.json'
gt = json.loads(gt_path.read_text())

lyrics_text = Path('/home/jordanc/workspace/rapclouds/standalone/lyrics/love_yourz.txt').read_text()
whisper_text = gt['text']

prompt = f"""You are correcting an AI transcription of a rap song against original lyrics.

ORIGINAL LYRICS (first 1500 chars):
{lyrics_text[:1500]}

WHISPER TRANSCRIPTION (first 1500 chars):
{whisper_text[:1500]}

Fix any words transcribed wrong (common in rap: AAVE, slang, proper nouns).
Return ONLY valid JSON:
{{"corrections": [{{"original": "wrong_word", "corrected": "right_word", "reason": "why"}}], "corrected_text": "full corrected text matching original lyrics"}}"""

headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
resp = requests.post('https://openrouter.ai/api/v1/chat/completions',
    headers=headers,
    json={'model': 'google/gemini-2.0-flash-001', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.1, 'max_tokens': 3000},
    timeout=60)

if resp.status_code == 200:
    content = resp.json()['choices'][0]['message']['content']
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        corrected = json.loads(match.group())
        corrections = corrected.get('corrections', [])
        print(f'LLM corrections: {len(corrections)}')
        for c in corrections[:15]:
            orig = c.get('original', '?')
            fixed = c.get('corrected', '?')
            reason = c.get('reason', '')
            print(f'  "{orig}" -> "{fixed}" ({reason})')
        
        gt['corrections'] = corrections
        gt['corrected_text'] = corrected.get('corrected_text', whisper_text)
        
        out_path = Path('/home/jordanc/workspace/karaoke-mvp/songs/love_yourz/ground_truth.json')
        with open(out_path, 'w') as f:
            json.dump(gt, f, indent=2)
        print(f'Saved corrected ground truth: {out_path}')
    else:
        print(f'Could not parse JSON from response')
        print(content[:300])
else:
    print(f'API error: {resp.status_code}')
