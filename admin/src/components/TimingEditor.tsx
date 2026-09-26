import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  Controls,
  useNodesState,
  BackgroundVariant,
} from '@xyflow/react';
import type { Node, NodeTypes } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import WordNode from './WordNode';
import ZoomControls from './ZoomControls';
import type { Word } from '../types';

interface Props {
  words: Word[];
  onTimingSave: (words: Word[]) => void;
}

const PX_PER_SECOND = 200;

function wordsToNodes(words: Word[], axis: 'x' | 'y'): Node[] {
  return words.map((w, i) => ({
    id: `word-${i}`,
    type: 'wordNode',
    position: axis === 'x'
      ? { x: w.start * PX_PER_SECOND, y: 0 }
      : { x: 0, y: w.start * PX_PER_SECOND },
    data: { word: w.word, start: w.start, end: w.end },
  }));
}

function nodesToWords(nodes: Node[], axis: 'x' | 'y'): Word[] {
  return nodes
    .slice()
    .sort((a, b) => axis === 'x'
      ? a.position.x - b.position.x
      : a.position.y - b.position.y
    )
    .map((n) => ({
      word: n.data.word as string,
      start: Math.max(0, (axis === 'x' ? n.position.x : n.position.y) / PX_PER_SECOND),
      end: Math.max(
        (axis === 'x' ? n.position.x : n.position.y) / PX_PER_SECOND + ((n.data.end as number) - (n.data.start as number)),
        0
      ),
    }));
}

export default function TimingEditor({ words, onTimingSave }: Props) {
  const [axis, setAxis] = useState<'x' | 'y'>('x');
  const initialNodes = useMemo(() => wordsToNodes(words, axis), []);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wordsRef = useRef(words);
  const hasSyncedRef = useRef(false);
  const axisRef = useRef(axis);

  useEffect(() => {
    axisRef.current = axis;
  }, [axis]);

  useEffect(() => {
    if (!hasSyncedRef.current) {
      hasSyncedRef.current = true;
      return;
    }
    setNodes(wordsToNodes(words, axis));
    wordsRef.current = words;
  }, [words, setNodes, axis]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleDragEnd = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const updatedWords = nodesToWords(nodes, axisRef.current);
      wordsRef.current = updatedWords;
      onTimingSave(updatedWords);
    }, 500);
  }, [nodes, onTimingSave]);

  const handleAxisChange = useCallback((newAxis: 'x' | 'y') => {
    setAxis(newAxis);
    setNodes(wordsToNodes(wordsRef.current, newAxis));
  }, [setNodes]);

  const nodeTypes: NodeTypes = useMemo(() => ({ wordNode: WordNode }), []);

  return (
    <div className="h-full bg-bg relative">
      <div className="absolute top-2 left-2 z-20 text-dim text-xs bg-bg/80 px-2 py-1 rounded">
        {words.length} words
      </div>
      <ReactFlow
        nodes={nodes}
        edges={[]}
        onNodesChange={onNodesChange}
        onNodeDragStop={handleDragEnd}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.3}
        maxZoom={2}
        style={{ background: '#0a0a0a' }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1a1a1a" />
        <MiniMap
          nodeColor="#1a1a1a"
          maskColor="rgba(0,0,0,0.5)"
          style={{ background: '#0a0a0a' }}
        />
        <Controls />
      </ReactFlow>
      <ZoomControls zoom={1} onZoomChange={() => {}} axis={axis} onAxisChange={handleAxisChange} />
    </div>
  );
}
