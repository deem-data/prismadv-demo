import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { CheckCircle2 } from 'lucide-react';

const ConstraintNode = ({ data }: NodeProps) => {
  return (
    <div className={`
      px-4 py-2 rounded-lg flex items-center gap-2 border-2 transition-all cursor-pointer
      ${data.highlighted ? 'border-accent-categorical shadow-[0_0_10px_rgba(40,167,69,0.5)]' : 'border-accent-categorical/60'}
      bg-accent-categorical/10 text-text-primary min-w-[150px]
    `}>
      <CheckCircle2 size={14} className="text-accent-categorical" />
      <div className="text-xs font-bold truncate tracking-tight">{data.label}</div>
      
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-accent-categorical" />
    </div>
  );
};

export default memo(ConstraintNode);
