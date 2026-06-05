import { DataTablePreview } from './DataTablePreview';
import { ColumnStatistics } from './ColumnStatistics';
import { DataQualityMetrics } from './DataQualityMetrics';
import { useAppStore } from '@/store';

export function LeftSidebar() {
  const {
    dataset,
    selectedColumn,
    columnStats,
    dataQualityMetrics,
    selectColumn,
  } = useAppStore();

  const stats = selectedColumn ? columnStats.get(selectedColumn) || null : null;

  return (
    <aside className="w-full h-full bg-dark-medium border-r border-dark-darkest flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Data Table Preview */}
        <DataTablePreview
          dataset={dataset}
          onColumnClick={selectColumn}
        />

        {/* Column Statistics */}
        <ColumnStatistics
          column={selectedColumn}
          stats={stats}
        />

        {/* Data Quality Metrics */}
        <DataQualityMetrics
          metrics={dataQualityMetrics}
          dataset={dataset}
        />
      </div>
    </aside>
  );
}

export default LeftSidebar;
