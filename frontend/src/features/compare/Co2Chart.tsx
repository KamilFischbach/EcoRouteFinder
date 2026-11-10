import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatCo2 } from '@/lib/format';
import type { ComparisonOption } from '@/types/comparison';
import { MODE_LABELS } from '@/types/trip';

// One series -> one hue (validated with the dataviz palette checker against the white surface).
const BAR_COLOR = '#059669'; // emerald-600
const MUTED_BAR_COLOR = '#d6d3d1'; // stone-300, impractical options (also labelled in the axis)
const AXIS_TEXT = '#78716c'; // stone-500
const GRID = '#e7e5e4'; // stone-200

interface ChartRow {
  label: string;
  co2: number;
  practical: boolean;
  note: string | null;
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: ChartRow }[];
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-stone-900">{row.label}</p>
      <p className="text-stone-600">{formatCo2(row.co2)} CO₂ per person</p>
      {!row.practical && row.note && <p className="mt-0.5 text-stone-500">{row.note}</p>}
    </div>
  );
}

export function Co2Chart({ options }: { options: ComparisonOption[] }) {
  const rows: ChartRow[] = options.map((option) => ({
    label: option.practical ? MODE_LABELS[option.mode] : `${MODE_LABELS[option.mode]} (n/a)`,
    co2: option.co2_kg,
    practical: option.practical,
    note: option.note,
  }));

  return (
    <figure>
      <figcaption className="mb-3 text-sm font-medium text-stone-700">
        CO₂ per person (kg)
        <span className="block text-xs font-normal text-stone-500">
          Grey bars are not practical for this distance. Exact values are in the cards below.
        </span>
      </figcaption>
      <div className="h-64 w-full" data-testid="co2-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
          >
            <CartesianGrid horizontal={false} stroke={GRID} />
            <XAxis
              type="number"
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={130}
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f5f5f4' }} />
            <Bar dataKey="co2" barSize={16} radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {rows.map((row) => (
                <Cell key={row.label} fill={row.practical ? BAR_COLOR : MUTED_BAR_COLOR} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
