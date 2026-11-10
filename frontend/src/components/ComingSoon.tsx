import { Card } from './Card';

interface ComingSoonProps {
  title: string;
  items: string[];
}

export function ComingSoon({ title, items }: ComingSoonProps) {
  return (
    <Card className="overflow-hidden">
      <div className="bg-linear-to-br from-emerald-50 to-lime-50 px-6 py-10 sm:px-10">
        <span className="inline-flex items-center rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
          Wkrótce
        </span>
        <h2 className="mt-4 text-lg font-semibold text-stone-900">{title}</h2>
        <ul className="mt-4 space-y-2 text-sm text-stone-700">
          {items.map((item) => (
            <li key={item} className="flex gap-2">
              <span
                aria-hidden="true"
                className="mt-1.5 size-1.5 shrink-0 rounded-full bg-emerald-500"
              />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
