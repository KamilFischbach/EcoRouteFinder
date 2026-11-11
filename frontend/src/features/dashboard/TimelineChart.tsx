import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { formatCo2 } from '@/lib/format';
import type { StatsGranularity, StatsTimelinePoint } from '@/types/stats';

import { periodLabel, periodTick } from './summary';

// Validated with the dataviz palette checker on white: CVD ΔE 16, contrast >= 3:1.
const FOOTPRINT_COLOR = '#0284c7'; // sky-600
const SAVED_COLOR = '#059669'; // emerald-600
const AXIS_TEXT = '#78716c'; // stone-500
const GRID = '#e7e5e4'; // stone-200

interface TimelineChartProps {
  timeline: StatsTimelinePoint[];
  granularity: StatsGranularity;
}

function ChartTooltip({
  active,
  payload,
  granularity,
}: {
  active?: boolean;
  payload?: { payload: StatsTimelinePoint }[];
  granularity: StatsGranularity;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-stone-900">{periodLabel(point.period_start, granularity)}</p>
      <p className="text-stone-600">Footprint: {formatCo2(point.co2_kg)}</p>
      <p className="text-stone-600">Saved vs petrol car: {formatCo2(point.co2_saved_kg)}</p>
      <p className="text-stone-500">
        {point.trips} {point.trips === 1 ? 'trip' : 'trips'}
      </p>
    </div>
  );
}

function Legend() {
  return (
    <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600" aria-hidden="true">
      <li className="flex items-center gap-1.5">
        <span className="size-2.5 rounded-sm bg-sky-600" /> CO₂ footprint
      </li>
      <li className="flex items-center gap-1.5">
        <span className="h-0.5 w-3 rounded-full bg-emerald-600" /> CO₂ saved vs petrol car
      </li>
    </ul>
  );
}

export function TimelineChart({ timeline, granularity }: TimelineChartProps) {
  return (
    <figure>
      <Legend />
      <div
        className="h-64 w-full"
        role="img"
        aria-label={`Chart: CO₂ footprint (bars) and CO₂ saved vs petrol car (line) per ${granularity}, in kg per person. The same data is in the table below.`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={timeline} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis
              dataKey="period_start"
              tickFormatter={(value: string) => periodTick(value, granularity)}
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              minTickGap={12}
            />
            <YAxis
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
              label={{
                value: 'kg CO₂',
                angle: -90,
                position: 'insideLeft',
                fill: AXIS_TEXT,
                fontSize: 12,
              }}
            />
            <ReferenceLine y={0} stroke={AXIS_TEXT} />
            <Tooltip
              content={<ChartTooltip granularity={granularity} />}
              cursor={{ fill: '#f5f5f4' }}
            />
            <Bar
              dataKey="co2_kg"
              fill={FOOTPRINT_COLOR}
              maxBarSize={28}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
            <Line
              dataKey="co2_saved_kg"
              stroke={SAVED_COLOR}
              strokeWidth={2}
              dot={{ r: 3, fill: SAVED_COLOR, strokeWidth: 0 }}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>CO₂ per {granularity}, kg per person</caption>
        <thead>
          <tr>
            <th scope="col">Period</th>
            <th scope="col">CO₂ footprint</th>
            <th scope="col">CO₂ saved vs petrol car</th>
            <th scope="col">Trips</th>
          </tr>
        </thead>
        <tbody>
          {timeline.map((point) => (
            <tr key={point.period_start}>
              <th scope="row">{periodLabel(point.period_start, granularity)}</th>
              <td>{formatCo2(point.co2_kg)}</td>
              <td>{formatCo2(point.co2_saved_kg)}</td>
              <td>{point.trips}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
