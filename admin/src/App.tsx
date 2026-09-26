import { useState, useCallback } from 'react';
import { fetchSong, updateSongText, updateSongTiming } from './api';
import type { GroundTruth } from './types';
import SongList from './components/SongList';
import LyricsEditor from './components/LyricsEditor';
import TimingEditor from './components/TimingEditor';

export default function App() {
  const [selectedSong, setSelectedSong] = useState<string | null>(null);
  const [songData, setSongData] = useState<GroundTruth | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSelectSong = useCallback(async (name: string) => {
    setSelectedSong(name);
    setLoading(true);
    try {
      const data = await fetchSong(name);
      setSongData(data);
    } catch (err) {
      console.error('Failed to load song:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleBack = useCallback(() => {
    setSelectedSong(null);
    setSongData(null);
  }, []);

  const handleTextSave = useCallback(
    async (text: string) => {
      if (!selectedSong) return;
      try {
        await updateSongText(selectedSong, text);
      } catch (err) {
        console.error('Failed to save text:', err);
      }
    },
    [selectedSong]
  );

  const handleTimingSave = useCallback(
    async (updatedWords: import('./types').Word[]) => {
      if (!selectedSong || !songData) return;
      const updated: GroundTruth = { ...songData, words: updatedWords };
      setSongData(updated);
      try {
        await updateSongTiming(selectedSong, updated);
      } catch (err) {
        console.error('Failed to save timing:', err);
      }
    },
    [selectedSong, songData]
  );

  if (!selectedSong) {
    return (
      <div className="min-h-screen bg-bg text-text font-sans">
        <header className="border-b border-surface2 px-6 py-4">
          <h1 className="text-xl font-bold text-accent">RapCheck Admin</h1>
        </header>
        <main className="p-6">
          <SongList onSelect={handleSelectSong} />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text font-sans flex flex-col">
      <header className="border-b border-surface2 px-6 py-4 flex items-center gap-4 shrink-0">
        <button
          onClick={handleBack}
          className="text-dim hover:text-text transition-colors text-sm"
        >
          &larr; Back
        </button>
        <h1 className="text-xl font-bold text-accent">RapCheck Admin</h1>
        <span className="text-dim text-sm ml-2">{selectedSong}</span>
      </header>
      <main className="flex-1 flex flex-col lg:flex-row min-h-0">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-dim">
            Loading...
          </div>
        ) : (
          <>
            <div className="flex-1 min-h-0 border-r border-surface2">
              {songData && (
                <LyricsEditor text={songData.text} onSave={handleTextSave} />
              )}
            </div>
            <div className="flex-1 min-h-0">
              {songData && (
                <TimingEditor words={songData.words} onTimingSave={handleTimingSave} />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
