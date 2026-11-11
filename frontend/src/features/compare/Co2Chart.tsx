import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatCo2, formatCo2Label } from '@/lib/format';
import type { ComparisonOption } from '@/types/comparison';
import { MODE_LABELS, type TransportMode } from '@/types/trip';

// One series -> one hue (validated with the dataviz palette checker against the white surface).
const BAR_COLOR = '#059669'; // emerald-600
// EcoAdvisor's pick, the app's AI accent. Validated against emerald-600: CVD ΔE 25, contrast >= 3:1.
const PICK_BAR_COLOR = '#7c3aed'; // violet-600
const MUTED_BAR_COLOR = '#d6d3d1'; // stone-300, impractical options (also labelled in the axis)
const AXIS_TEXT = '#78716c'; // stone-500
const GRID = '#e7e5e4'; // stone-200

interface ChartRow {
  label: string;
  co2: number;
  practical: boolean;
  pick: boolean;
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
      {row.pick && <p className="mt-0.5 font-medium text-violet-700">EcoAdvisor pick</p>}
      {!row.practical && row.note && <p className="mt-0.5 text-stone-500">{row.note}</p>}
    </div>
  );
}

function rowLabel(option: ComparisonOption, pick: boolean): string {
  const label = MODE_LABELS[option.mode];
  if (!option.practical) return `${label} (n/a)`;
  return pick ? `${label} (pick)` : label;
}

interface Co2ChartProps {
  options: ComparisonOption[];
  /** EcoAdvisor's recommendation: drawn in violet and labelled "(pick)". */
  recommended?: TransportMode | null;
}

function barColor(row: ChartRow): string {
  if (!row.practical) return MUTED_BAR_COLOR;
  return row.pick ? PICK_BAR_COLOR : BAR_COLOR;
}

export function Co2Chart({ options, recommended = null }: Co2ChartProps) {
  const rows: ChartRow[] = options.map((option) => {
    const pick = option.mode === recommended;
    return {
      label: rowLabel(option, pick),
      co2: option.co2_kg,
      practical: option.practical,
      pick,
      note: option.note,
    };
  });

  return (
    <figure>
      <figcaption className="mb-3 text-sm font-medium text-stone-700">
        CO₂ per person (kg)
        <span className="block text-xs font-normal text-stone-500">
          Grey bars are not practical for this distance.
          {recommended && ' The violet bar is EcoAdvisor’s pick.'} Exact values are in the cards
          below.
        </span>
      </figcaption>
      <div className="h-64 w-full" data-testid="co2-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 0, right: 64, bottom: 0, left: 0 }}
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
            <Bar
              dataKey="co2"
              barSize={16}
              radius={[0, 4, 4, 0]}
              minPointSize={3}
              isAnimationActive={false}
            >
              {/* A bar of a few pixels and a value label keep 0 kg (the bike) visible. */}
              <LabelList
                dataKey="co2"
                position="right"
                formatter={formatCo2Label}
                fill={AXIS_TEXT}
                fontSize={12}
              />
              {rows.map((row) => (
                <Cell key={row.label} fill={barColor(row)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
