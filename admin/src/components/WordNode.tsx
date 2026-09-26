import { Handle, Position } from '@xyflow/react';

interface WordNodeData {
  word: string;
  start: number;
  end: number;
  [key: string]: unknown;
}

const PX_PER_SECOND = 200;

export default function WordNode({ data }: { data: WordNodeData }) {
  const { word, start, end } = data;
  const duration = end - start;
  const width = Math.max(duration * PX_PER_SECOND, 40);

  return (
    <div
      className="bg-surface2 border border-dim text-text rounded-lg flex flex-col items-center justify-center px-2 py-1"
      style={{ width, minHeight: 48 }}
    >
      <Handle type="target" position={Position.Left} className="!bg-dim" />
      <div
        className="text-sm font-medium text-center w-full truncate"
      >
        {word}
      </div>
      <div className="text-[10px] text-dim mt-0.5">
        {start.toFixed(2)}s – {end.toFixed(2)}s
      </div>
      <Handle type="source" position={Position.Right} className="!bg-dim" />
    </div>
  );
}
