import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Database } from 'lucide-react';

const DataNode = ({ data }: NodeProps) => {
  return (
    <div className={`
      px-4 py-2 rounded-full flex items-center gap-2 border-2 transition-all
      ${data.highlighted ? 'border-accent-textual shadow-[0_0_10px_rgba(74,144,226,0.5)]' : 'border-accent-textual/60'}
      bg-accent-textual/10 text-text-primary min-w-[120px]
    `}>
      <Database size={14} className="text-accent-textual" />
      <div className="text-xs font-bold truncate">{data.label}</div>

      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-accent-textual" />
      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-accent-textual" />
    </div>
  );
};

export default memo(DataNode);
