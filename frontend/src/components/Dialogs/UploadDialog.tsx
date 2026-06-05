import * as Dialog from '@radix-ui/react-dialog';
import { X, Upload, Database, CheckCircle } from 'lucide-react';
import { useRef, useState } from 'react';
import { useAppStore } from '@/store';

interface UploadDialogProps {
  open: boolean;
  onClose: () => void;
}

export function UploadDialog({ open, onClose }: UploadDialogProps) {
  const { uploadTaskFile, uploadDataset, taskFile, dataset } = useAppStore();

  const taskFileInputRef = useRef<HTMLInputElement>(null);
  const datasetInputRef = useRef<HTMLInputElement>(null);

  const [uploadingTask, setUploadingTask] = useState(false);
  const [uploadingDataset, setUploadingDataset] = useState(false);

  const handleTaskFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingTask(true);
    try {
      await uploadTaskFile(file);
    } finally {
      setUploadingTask(false);
      if (taskFileInputRef.current) taskFileInputRef.current.value = '';
    }
  };

  const handleDataset = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingDataset(true);
    try {
      await uploadDataset(file);
    } finally {
      setUploadingDataset(false);
      if (datasetInputRef.current) datasetInputRef.current.value = '';
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-dark-light border border-dark-border rounded-lg shadow-xl z-50 w-[520px]">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-dark-border">
            <Dialog.Title className="text-lg font-semibold text-text-primary">
              Upload your own
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-text-secondary hover:text-text-primary transition-colors">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          {/* Two upload zones */}
          <div className="grid grid-cols-2 divide-x divide-dark-border">
            {/* Task Code */}
            <div className="p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Upload size={15} className="text-text-muted" />
                <span className="text-sm font-medium text-text-secondary">Task Code</span>
              </div>
              <p className="text-xs text-text-muted">Python or SQL script</p>

              {taskFile && (
                <div className="flex items-center gap-1.5 text-xs text-green-400">
                  <CheckCircle size={13} />
                  <span className="truncate">{taskFile.name}</span>
                </div>
              )}

              <button
                onClick={() => taskFileInputRef.current?.click()}
                disabled={uploadingTask}
                className={`mt-auto flex items-center justify-center gap-2 px-3 py-2 rounded text-sm border transition-colors ${
                  uploadingTask
                    ? 'border-dark-border text-text-muted cursor-not-allowed'
                    : 'border-dark-border text-text-secondary hover:border-accent-blue hover:text-accent-blue'
                }`}
              >
                <Upload size={14} />
                {uploadingTask ? 'Uploading…' : taskFile ? 'Replace' : 'Choose file'}
              </button>
              <input
                ref={taskFileInputRef}
                type="file"
                accept=".py,.sql"
                onChange={handleTaskFile}
                className="hidden"
              />
            </div>

            {/* Dataset */}
            <div className="p-5 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Database size={15} className="text-text-muted" />
                <span className="text-sm font-medium text-text-secondary">Dataset</span>
              </div>
              <p className="text-xs text-text-muted">CSV file</p>

              {dataset && (
                <div className="flex items-center gap-1.5 text-xs text-green-400">
                  <CheckCircle size={13} />
                  <span className="truncate">{dataset.name}</span>
                </div>
              )}

              <button
                onClick={() => datasetInputRef.current?.click()}
                disabled={uploadingDataset}
                className={`mt-auto flex items-center justify-center gap-2 px-3 py-2 rounded text-sm border transition-colors ${
                  uploadingDataset
                    ? 'border-dark-border text-text-muted cursor-not-allowed'
                    : 'border-dark-border text-text-secondary hover:border-accent-blue hover:text-accent-blue'
                }`}
              >
                <Database size={14} />
                {uploadingDataset ? 'Uploading…' : dataset ? 'Replace' : 'Choose file'}
              </button>
              <input
                ref={datasetInputRef}
                type="file"
                accept=".csv"
                onChange={handleDataset}
                className="hidden"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end px-6 py-3 border-t border-dark-border">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded text-sm font-medium bg-accent-blue text-white hover:bg-accent-blue/90 transition-colors"
            >
              Done
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
