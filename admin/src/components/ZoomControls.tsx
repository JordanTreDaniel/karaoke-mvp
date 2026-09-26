interface ZoomControlsProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  axis: 'x' | 'y';
  onAxisChange: (axis: 'x' | 'y') => void;
}

const ZOOM_MIN = 25;
const ZOOM_MAX = 400;
const ZOOM_STEP = 25;

export default function ZoomControls({ zoom, onZoomChange, axis, onAxisChange }: ZoomControlsProps) {
  const handleZoomIn = () => onZoomChange(Math.min(zoom + ZOOM_STEP, ZOOM_MAX));
  const handleZoomOut = () => onZoomChange(Math.max(zoom - ZOOM_STEP, ZOOM_MIN));
  const handleAxisToggle = () => onAxisChange(axis === 'x' ? 'y' : 'x');

  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-center gap-1 rounded-lg border border-surface2 bg-surface px-2 py-1 shadow-lg">
      <button
        onClick={handleZoomOut}
        className="flex h-7 w-7 items-center justify-center rounded text-text hover:bg-surface2"
        aria-label="Zoom out"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="7" x2="11" y2="7" />
        </svg>
      </button>

      <span className="min-w-[3rem] text-center text-xs text-dim">{zoom}%</span>

      <button
        onClick={handleZoomIn}
        className="flex h-7 w-7 items-center justify-center rounded text-text hover:bg-surface2"
        aria-label="Zoom in"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="7" x2="11" y2="7" />
          <line x1="7" y1="3" x2="7" y2="11" />
        </svg>
      </button>

      <div className="mx-1 h-5 w-px bg-surface2" />

      <button
        onClick={handleAxisToggle}
        className="flex h-7 items-center gap-1 rounded px-2 text-xs text-text hover:bg-surface2"
        aria-label={`Switch to time-on-${axis === 'x' ? 'Y' : 'X'} layout`}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 11V3h8" />
          <path d="M3 11l3-3 2 2 3-4" />
        </svg>
        {axis === 'x' ? 'Time→X' : 'Time→Y'}
      </button>
    </div>
  );
}
