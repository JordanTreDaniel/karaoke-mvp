import { useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';

interface Props {
  text: string;
  onSave: (text: string) => void;
}

export default function LyricsEditor({ text, onSave }: Props) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const internalTextRef = useRef(text);
  const editorRef = useRef<Parameters<NonNullable<React.ComponentProps<typeof Editor>['onMount']>>[0] | null>(null);

  useEffect(() => {
    if (internalTextRef.current !== text) {
      internalTextRef.current = text;
      if (editorRef.current) {
        const model = editorRef.current.getModel();
        if (model && model.getValue() !== text) {
          const position = editorRef.current.getPosition();
          model.setValue(text);
          if (position) editorRef.current.setPosition(position);
        }
      }
    }
  }, [text]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleChange = (value: string | undefined) => {
    if (value === undefined) return;
    internalTextRef.current = value;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onSave(value);
    }, 1000);
  };

  const wordCount = internalTextRef.current.trim().split(/\s+/).filter(Boolean).length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="plaintext"
          theme="vs-dark"
          value={text}
          onChange={handleChange}
          onMount={(editor) => {
            editorRef.current = editor;
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            automaticLayout: true,
            padding: { top: 12 },
            domReadOnly: false,
          }}
        />
      </div>
      <div className="shrink-0 px-4 py-2 border-t border-surface2 text-dim text-xs">
        {wordCount} words
      </div>
    </div>
  );
}
