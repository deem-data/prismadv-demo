import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Tooltip from '@radix-ui/react-tooltip';
import { Download } from 'lucide-react';
import type { Constraint, ExportFormat } from '@/types';
import { useAppStore } from '@/store';

interface ExportButtonProps {
  constraints: Constraint[];
}

function generateGE(constraints: Constraint[]): string {
  const lines = [
    '"""Auto-generated Great Expectations validation suite."""',
    'import great_expectations as gx',
    '',
    '',
    'def validate(context, dataset_path: str):',
    '    datasource = context.sources.add_or_update_pandas("pandas_datasource")',
    '    asset = datasource.add_csv_asset("dataset", filepath_or_buffer=dataset_path)',
    '    batch_request = asset.build_batch_request()',
    '    validator = context.get_validator(batch_request=batch_request)',
    '',
  ];
  for (const c of constraints) {
    if (c.code.greatExpectations) {
      lines.push(`    # ${c.label} (${c.column})`);
      lines.push(`    validator.${c.code.greatExpectations}`);
      lines.push('');
    }
  }
  lines.push('    return validator.validate()');
  lines.push('');
  return lines.join('\n');
}

function generateDeequ(constraints: Constraint[]): string {
  const lines = [
    '// Auto-generated Deequ validation suite',
    'import com.amazon.deequ.checks.{Check, CheckLevel}',
    'import com.amazon.deequ.VerificationSuite',
    '',
    'val check = Check(CheckLevel.Warning, "PrismaDV generated constraints")',
  ];
  for (const c of constraints) {
    if (c.code.deequ) {
      lines.push(`  // ${c.label} (${c.column})`);
      lines.push(`  ${c.code.deequ}`);
    }
  }
  lines.push('');
  lines.push('val result = VerificationSuite()');
  lines.push('  .onData(df)');
  lines.push('  .addCheck(check)');
  lines.push('  .run()');
  lines.push('');
  return lines.join('\n');
}

function generateJSON(constraints: Constraint[]): string {
  const data = constraints.map((c) => ({
    id: c.id,
    column: c.column,
    type: c.type,
    label: c.label,
    code: c.code,
    assumption: { text: c.assumption.text },
  }));
  return JSON.stringify({ constraints: data }, null, 2);
}

function downloadFile(content: string, format: ExportFormat) {
  const extensions: Record<ExportFormat, string> = {
    great_expectations: 'py',
    deequ: 'scala',
    json: 'json',
  };
  const mimeTypes: Record<ExportFormat, string> = {
    great_expectations: 'text/x-python',
    deequ: 'text/x-scala',
    json: 'application/json',
  };
  const blob = new Blob([content], { type: mimeTypes[format] });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `prismadv_constraints.${extensions[format]}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function ExportButton({ constraints }: ExportButtonProps) {
  const addToast = useAppStore((state) => state.addToast);
  const hasConstraints = constraints.length > 0;

  const handleExport = (format: ExportFormat) => {
    try {
      const enabled = constraints.filter((c) => c.enabled);
      let content: string;
      if (format === 'great_expectations') {
        content = generateGE(enabled);
      } else if (format === 'deequ') {
        content = generateDeequ(enabled);
      } else {
        content = generateJSON(enabled);
      }
      downloadFile(content, format);
      addToast({
        type: 'success',
        message: `Exported ${enabled.length} constraints as ${format}`,
      });
    } catch (error) {
      addToast({
        type: 'error',
        message: `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    }
  };

  const buttonClass = `flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-all ${
    hasConstraints
      ? 'bg-accent-blue text-white hover:bg-accent-blue/90'
      : 'bg-dark-border text-text-muted cursor-not-allowed'
  }`;

  if (!hasConstraints) {
    return (
      <Tooltip.Provider delayDuration={300}>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <span className="inline-flex">
              <button disabled className={buttonClass}>
                <Download size={16} />
                <span>Export</span>
              </button>
            </span>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              className="bg-dark-medium border border-dark-border rounded px-3 py-1.5 text-xs text-text-secondary shadow-lg z-50"
              sideOffset={5}
            >
              Generate constraints first to enable export
              <Tooltip.Arrow className="fill-dark-medium" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
    );
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className={buttonClass}>
          <Download size={16} />
          <span>Export</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="min-w-[240px] bg-dark-light border border-dark-border rounded-md shadow-lg p-1 z-50"
          sideOffset={5}
        >
          <DropdownMenu.Item
            className="flex flex-col gap-0.5 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
            onSelect={() => handleExport('great_expectations')}
          >
            <span className="font-medium">Great Expectations (Python)</span>
            <span className="text-xs opacity-70">Export as GE validation suite</span>
          </DropdownMenu.Item>

          <DropdownMenu.Item
            className="flex flex-col gap-0.5 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
            onSelect={() => handleExport('deequ')}
          >
            <span className="font-medium">Deequ (Scala)</span>
            <span className="text-xs opacity-70">Export as Deequ verification suite</span>
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="h-px bg-dark-border my-1" />

          <DropdownMenu.Item
            className="flex flex-col gap-0.5 px-3 py-2 text-sm text-text-secondary hover:bg-dark-border hover:text-text-primary rounded cursor-pointer outline-none"
            onSelect={() => handleExport('json')}
          >
            <span className="font-medium">JSON</span>
            <span className="text-xs opacity-70">Export constraints as JSON</span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
