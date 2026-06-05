import React from 'react';
import { Lightbulb, ArrowRight } from 'lucide-react';
import { Assumption } from '@/types';
import { useAppStore } from '@/store';

interface AssumptionCardProps {
  assumption: Assumption;
  assumptionId?: string;
}

const AssumptionCard: React.FC<AssumptionCardProps> = ({ assumption, assumptionId }) => {
  const { selectAssumption } = useAppStore();

  return (
    <div className="bg-dark-light border border-dark-border rounded p-3">
      <div className="flex items-start gap-2 mb-2 min-w-0">
        <Lightbulb size={16} className="text-yellow-500 shrink-0 mt-0.5" />
        <div className="text-sm text-text-primary leading-snug min-w-0 break-words">
          {assumption.text}
        </div>
      </div>

      {assumptionId && (
        <div className="flex items-center justify-end text-xs mt-3 pt-2 border-t border-dark-border">
          <button
            onClick={() => selectAssumption(assumptionId)}
            className="flex items-center gap-1 text-accent-textual hover:text-blue-400 transition-colors"
          >
            <span>Go to assumption</span>
            <ArrowRight size={10} />
          </button>
        </div>
      )}
    </div>
  );
};

export default AssumptionCard;
