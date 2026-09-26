import { useState, useEffect } from 'react';
import { fetchSongs } from '../api';
import type { SongMeta } from '../types';

interface Props {
  onSelect: (name: string) => void;
}

export default function SongList({ onSelect }: Props) {
  const [songs, setSongs] = useState<SongMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSongs()
      .then((data) => {
        if (!cancelled) setSongs(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load songs');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-dim border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <div className="text-red text-lg font-medium mb-2">Error loading songs</div>
        <div className="text-dim text-sm">{error}</div>
      </div>
    );
  }

  if (songs.length === 0) {
    return (
      <div className="text-center py-20 text-dim">
        <div className="text-lg mb-2">No songs found</div>
        <div className="text-sm">Add songs to get started.</div>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {songs.map((song) => (
        <button
          key={song.name}
          onClick={() => onSelect(song.name)}
          className="text-left p-4 rounded-lg bg-surface border border-surface2 hover:border-accent transition-colors cursor-pointer"
        >
          <div className="font-medium text-text truncate">{song.name}</div>
          <div className="text-sm text-dim mt-1">
            {song.duration.toFixed(1)}s &middot; {song.words} words
          </div>
        </button>
      ))}
    </div>
  );
}
