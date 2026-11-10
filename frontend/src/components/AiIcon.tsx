import { cn } from '@/lib/cn';

/** Sparkles marker for AI-powered actions (public/ai-icon.png). Decorative only. */
export function AiIcon({ className }: { className?: string }) {
  return <img src="/ai-icon.png" alt="" aria-hidden="true" className={cn('size-4', className)} />;
}
