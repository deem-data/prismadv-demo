import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FileCode } from 'lucide-react';

const CodeNode = ({ data }: NodeProps) => {
  return (
    <div className={`
      px-4 py-2 rounded-md flex items-center gap-2 border-2 transition-all
      ${data.highlighted ? 'border-accent-purple shadow-[0_0_10px_rgba(197,134,192,0.35)]' : 'border-accent-purple/60'}
      bg-accent-purple/10 text-text-primary min-w-[140px]
    `}>
      <FileCode size={14} className="text-accent-purple" />
      <div className="text-xs font-bold truncate">{data.label}</div>
      
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-accent-purple" />
      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-accent-purple" />
    </div>
  );
};

export default memo(CodeNode);
