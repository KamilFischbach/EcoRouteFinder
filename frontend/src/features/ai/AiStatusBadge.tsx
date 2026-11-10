import { cn } from '@/lib/cn';

import { useHealthQuery } from './useAiStatus';

type Tone = 'online' | 'offline' | 'down';

const DOT: Record<Tone, string> = {
  online: 'bg-emerald-500',
  offline: 'bg-stone-400',
  down: 'bg-red-500',
};

/** "AI online · qwen3:8b" / "AI offline (rule-based)". Text collapses to a dot on phones. */
export function AiStatusBadge() {
  const { data, isPending, isError } = useHealthQuery();
  if (isPending) return null;

  let tone: Tone;
  let label: string;
  if (isError) {
    tone = 'down';
    label = 'API offline';
  } else if (data.ai_available) {
    tone = 'online';
    label = data.ai_model ? `AI online · ${data.ai_model}` : 'AI online';
  } else {
    tone = 'offline';
    label = 'AI offline (rule-based)';
  }

  return (
    <span
      role="status"
      title={label}
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium text-stone-600 md:bg-stone-100/80 md:px-2.5"
    >
      <span aria-hidden="true" className={cn('size-2 rounded-full', DOT[tone])} />
      <span className="sr-only md:not-sr-only">{label}</span>
    </span>
  );
}
