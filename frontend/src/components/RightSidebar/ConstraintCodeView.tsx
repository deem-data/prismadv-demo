import React, { useState } from 'react';
import { Copy, Check, Play, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { ConstraintCode } from '@/types';

interface ValidationInfo {
  status: 'pass' | 'fail' | 'error';
  message?: string;
}

interface ConstraintCodeViewProps {
  code: ConstraintCode;
  geValidation?: ValidationInfo | null;
  deequValidation?: ValidationInfo | null;
  onValidateGe?: () => void;
  onValidateDeequ?: () => void;
  isValidatingGe?: boolean;
  isValidatingDeequ?: boolean;
}

function ValidationBadge({ info }: { info: ValidationInfo }) {
  return (
    <div className={`px-3 py-2 text-xs ${
      info.status === 'pass' ? 'bg-green-500/5' :
      info.status === 'fail' ? 'bg-red-500/5' :
      'bg-yellow-500/5'
    }`}>
      <div className="flex items-center gap-1.5 mb-0.5">
        {info.status === 'pass' ? (
          <><CheckCircle2 size={12} className="text-green-500 flex-shrink-0" /><span className="text-green-400 font-medium">Passed</span></>
        ) : info.status === 'fail' ? (
          <><XCircle size={12} className="text-red-500 flex-shrink-0" /><span className="text-red-400 font-medium">Violated</span></>
        ) : (
          <><AlertCircle size={12} className="text-yellow-500 flex-shrink-0" /><span className="text-yellow-400 font-medium">Evaluation Error</span></>
        )}
      </div>
      {info.message && (
        <p className="text-text-muted leading-relaxed pl-[18px]">{info.message}</p>
      )}
    </div>
  );
}

function ValidateButton({ onClick, isLoading, label }: { onClick: () => void; isLoading: boolean; label: string }) {
  return (
    <div className="px-3 py-2 border-t border-dark-border">
      <button
        onClick={onClick}
        disabled={isLoading}
        className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded transition-colors
          bg-dark-medium border border-dark-border hover:border-accent-textual hover:text-accent-textual
          text-text-secondary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <><Loader2 size={11} className="animate-spin" />Validating...</>
        ) : (
          <><Play size={11} />{label}</>
        )}
      </button>
    </div>
  );
}

const ConstraintCodeView: React.FC<ConstraintCodeViewProps> = ({
  code,
  geValidation,
  deequValidation,
  onValidateGe,
  onValidateDeequ,
  isValidatingGe,
  isValidatingDeequ,
}) => {
  const [activeTab, setActiveTab] = useState<'ge' | 'deequ'>('ge');
  const [copied, setCopied] = useState(false);

  const currentCode = activeTab === 'ge' ? code.greatExpectations : code.deequ;
  const hasCode = !!currentCode;

  const handleCopy = () => {
    if (!currentCode) return;
    navigator.clipboard.writeText(currentCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabValidation = activeTab === 'ge' ? geValidation : deequValidation;

  // Tab status icon helper
  const statusIcon = (info: ValidationInfo | null | undefined) => {
    if (!info) return null;
    if (info.status === 'pass') return <CheckCircle2 size={11} className="text-green-500" />;
    if (info.status === 'fail') return <XCircle size={11} className="text-red-500" />;
    return <AlertCircle size={11} className="text-yellow-500" />;
  };

  return (
    <div className="bg-dark-darkest border border-dark-border rounded overflow-hidden min-w-0">
      {/* Tabs */}
      <div className="flex border-b border-dark-border bg-dark-medium">
        <button
          onClick={() => setActiveTab('ge')}
          className={`
            flex-1 px-3 py-2 text-xs font-medium transition-colors flex items-center justify-center gap-1.5
            ${activeTab === 'ge'
              ? 'text-text-primary bg-dark-darkest border-t-2 border-accent-textual'
              : 'text-text-muted hover:text-text-secondary hover:bg-dark-light border-t-2 border-transparent'}
          `}
        >
          Great Expectations
          {statusIcon(geValidation)}
        </button>
        <button
          onClick={() => setActiveTab('deequ')}
          className={`
            flex-1 px-3 py-2 text-xs font-medium transition-colors flex items-center justify-center gap-1.5
            ${activeTab === 'deequ'
              ? 'text-text-primary bg-dark-darkest border-t-2 border-accent-textual'
              : 'text-text-muted hover:text-text-secondary hover:bg-dark-light border-t-2 border-transparent'}
          `}
        >
          Deequ
          {statusIcon(deequValidation)}
        </button>
      </div>

      {/* Code Block */}
      <div className="relative group">
        {hasCode ? (
          <pre className="p-3 text-xs text-text-secondary font-mono leading-relaxed whitespace-pre-wrap break-words">
            {currentCode}
          </pre>
        ) : (
          <div className="p-3 text-xs text-text-muted italic">
            No {activeTab === 'ge' ? 'Great Expectations' : 'Deequ'} code available
          </div>
        )}

        {hasCode && (
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1.5 rounded bg-dark-medium text-text-muted hover:text-text-primary opacity-0 group-hover:opacity-100 transition-opacity"
            title="Copy code"
          >
            {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
          </button>
        )}
      </div>

      {/* Validation result + button */}
      {hasCode && (
        <div className="border-t border-dark-border">
          {tabValidation ? (
            <ValidationBadge info={tabValidation} />
          ) : (
            <div className="px-3 py-1.5 text-[10px] text-text-muted">
              Not yet validated against the dataset
            </div>
          )}

          {activeTab === 'ge' && onValidateGe && code.greatExpectations && (
            <ValidateButton onClick={onValidateGe} isLoading={!!isValidatingGe} label="Validate on Dataset" />
          )}
          {activeTab === 'deequ' && onValidateDeequ && code.deequ && (
            <ValidateButton onClick={onValidateDeequ} isLoading={!!isValidatingDeequ} label="Validate on Dataset" />
          )}
        </div>
      )}
    </div>
  );
};

export default ConstraintCodeView;
