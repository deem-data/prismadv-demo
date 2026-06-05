import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Table as TableIcon } from 'lucide-react';
import type { Dataset } from '@/types';
import apiClient from '@/api';

interface DataTablePreviewProps {
  dataset: Dataset | null;
  onColumnClick?: (column: string) => void;
}

export function DataTablePreview({ dataset, onColumnClick }: DataTablePreviewProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);

  useEffect(() => {
    if (!dataset) return;
    let cancelled = false;
    apiClient
      .getDatasetPreview(dataset.id, 5)
      .then((preview) => {
        if (!cancelled) setPreviewData(preview.rows);
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn(`Failed to load dataset preview for ${dataset.id}:`, error);
          setPreviewData([]);
        }
      });
    return () => { cancelled = true; };
  }, [dataset]);

  if (!dataset) {
    return (
      <section className="bg-dark-light rounded-lg p-3 border border-dark-border">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <TableIcon size={16} />
          <span>No dataset loaded</span>
        </div>
      </section>
    );
  }

  const getColumnBorderClassName = (columnName: string) => {
    const column = dataset.columns.find((c) => c.name === columnName);
    if (!column) return 'border-l-[3px] border-text-muted';

    switch (column.inferredType) {
      case 'textual':
        return 'border-l-[3px] border-accent-textual';
      case 'numerical':
        return 'border-l-[3px] border-accent-numerical';
      case 'categorical':
        return 'border-l-[3px] border-accent-categorical';
      default:
        return 'border-l-[3px] border-text-muted';
    }
  };

  return (
    <section className="bg-dark-light rounded-lg border border-dark-border overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2 p-3 hover:bg-dark-border/50 transition-colors text-left"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        <TableIcon size={16} className="text-accent-blue" />
        <span className="font-medium text-sm text-text-secondary flex-1">
          Data Table
        </span>
      </button>

      {/* Content */}
      {!collapsed && (
        <div className="p-3 pt-0 space-y-2">
          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-dark-border">
                  {dataset.columns.map((column) => (
                    <th
                      key={column.name}
                      onClick={() => onColumnClick?.(column.name)}
                      className={`px-2 py-1.5 text-left font-medium text-text-secondary cursor-pointer hover:bg-dark-border/70 transition-colors ${getColumnBorderClassName(column.name)}`}
                    >
                      {column.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.map((row, idx) => (
                  <tr
                    key={idx}
                    className={idx % 2 === 0 ? 'bg-dark-light' : 'bg-dark-medium'}
                  >
                    {dataset.columns.map((column) => (
                      <td
                        key={column.name}
                        className="px-2 py-1 text-text-primary font-mono"
                      >
                        {String(row[column.name] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="text-center text-xs text-text-muted pt-2 border-t border-dark-border">
            📊 {dataset.columnCount} columns × {dataset.rowCount} rows
          </div>
        </div>
      )}
    </section>
  );
}
