import type { GroundTruth, SongMeta } from './types';

export async function fetchSongs(): Promise<SongMeta[]> {
  const res = await fetch('/api/songs');
  if (!res.ok) throw new Error(`Failed to fetch songs: ${res.status}`);
  return res.json();
}

export async function fetchSong(name: string): Promise<GroundTruth> {
  const res = await fetch(`/api/songs/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`Failed to fetch song: ${res.status}`);
  return res.json();
}

export async function updateSongText(name: string, text: string): Promise<void> {
  const res = await fetch(`/api/songs/${encodeURIComponent(name)}/text`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Failed to update text: ${res.status}`);
}

export async function updateSongTiming(name: string, timing: GroundTruth): Promise<void> {
  const res = await fetch(`/api/songs/${encodeURIComponent(name)}/timing`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(timing),
  });
  if (!res.ok) throw new Error(`Failed to update timing: ${res.status}`);
}
