import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Lightbulb } from 'lucide-react';

const AssumptionNode = ({ data }: NodeProps) => {
  return (
    <div className={`
      relative px-4 py-2 flex items-center gap-2 border-2 transition-all cursor-pointer
      ${data.highlighted ? 'border-accent-numerical shadow-[0_0_10px_rgba(245,158,66,0.5)]' : 'border-accent-numerical/60'}
      bg-accent-numerical/10 text-text-primary min-w-[130px] rounded-sm
    `}>
      {/* Visual diamond shape for background would be complex with CSS alone, 
          using a styled container with rounded-sm for now */}
      <Lightbulb size={14} className="text-accent-numerical" />
      <div className="text-xs font-bold truncate">{data.label}</div>
      
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-accent-numerical" />
      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-accent-numerical" />
    </div>
  );
};

export default memo(AssumptionNode);
