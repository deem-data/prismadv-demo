import React, { useState } from 'react';
import { useAppStore } from '@/store';
import { FileCode, ChevronDown, Pencil, Lock, Loader2 } from 'lucide-react';
import { EditorSettings } from './EditorSettings';

const CodeToolbar: React.FC = () => {
  const { taskFile, code, codeEditable, setCodeEditable, uploadTaskFile } = useAppStore();
  const [syncing, setSyncing] = useState(false);

  const handleToggle = async () => {
    if (codeEditable) {
      // Locking: re-upload if code changed
      if (taskFile && code !== taskFile.content) {
        setSyncing(true);
        try {
          const file = new File([code], taskFile.name, { type: 'text/plain' });
          await uploadTaskFile(file);
        } finally {
          setSyncing(false);
        }
      }
      setCodeEditable(false);
    } else {
      setCodeEditable(true);
    }
  };

  return (
    <div className="h-10 flex items-center justify-between px-4 bg-dark-light border-b border-dark-darkest select-none">
      <div className="flex items-center space-x-3">
        <div className="flex items-center text-text-secondary hover:text-text-primary transition-colors cursor-pointer">
          <FileCode size={16} className="mr-2 text-accent-textual" />
          <span className="text-sm font-medium">
            {taskFile?.name || 'no file selected'}
          </span>
          <ChevronDown size={14} className="ml-1 opacity-50" />
        </div>

        {taskFile && (
          <div className="text-[10px] px-1.5 py-0.5 rounded bg-dark-darkest text-text-muted uppercase tracking-wider font-bold">
            {taskFile.language}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={handleToggle}
          disabled={syncing}
          title={codeEditable ? 'Lock editor (saves changes)' : 'Unlock editor (editable)'}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors ${
            syncing
              ? 'text-text-muted cursor-not-allowed'
              : codeEditable
              ? 'text-accent-blue bg-accent-blue/10 hover:bg-accent-blue/20'
              : 'text-text-secondary hover:text-text-primary hover:bg-dark-medium'
          }`}
        >
          {syncing
            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
            : codeEditable
            ? <Pencil className="w-3.5 h-3.5" />
            : <Lock className="w-3.5 h-3.5" />}
          <span>{syncing ? 'Saving…' : codeEditable ? 'Editing' : 'Read-only'}</span>
        </button>
        <EditorSettings />
      </div>
    </div>
  );
};

export default CodeToolbar;
