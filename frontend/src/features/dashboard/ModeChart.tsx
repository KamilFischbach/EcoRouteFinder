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

import { MODE_CHART_COLORS } from '@/features/trips/modeColors';
import { cn } from '@/lib/cn';
import { formatCo2, formatCo2Label, formatDistance } from '@/lib/format';
import type { StatsByMode } from '@/types/stats';
import { MODE_LABELS } from '@/types/trip';

const AXIS_TEXT = '#78716c'; // stone-500
const GRID = '#e7e5e4'; // stone-200

interface Row extends StatsByMode {
  label: string;
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: Row }[] }) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-stone-900">{row.label}</p>
      <p className="text-stone-600">{formatCo2(row.co2_kg)} CO₂ per person</p>
      <p className="text-stone-500">
        {row.trips} {row.trips === 1 ? 'trip' : 'trips'} · {formatDistance(row.distance_km)}
      </p>
    </div>
  );
}

/** Horizontal bars, one per mode; each bar is labelled on the axis, so colour is only a hint. */
export function ModeChart({ byMode }: { byMode: StatsByMode[] }) {
  const rows: Row[] = byMode.map((mode) => ({ ...mode, label: MODE_LABELS[mode.mode] }));
  return (
    <figure>
      <div
        className={cn('w-full', rows.length > 3 ? 'h-60' : 'h-40')}
        role="img"
        aria-label="Chart: CO₂ footprint by transport mode in kg per person. The same data is in the table below."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 0, right: 64, bottom: 20, left: 0 }}
          >
            <CartesianGrid horizontal={false} stroke={GRID} />
            <XAxis
              type="number"
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
              label={{
                value: 'kg CO₂ per person',
                position: 'insideBottom',
                offset: -12,
                fill: AXIS_TEXT,
                fontSize: 12,
              }}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={96}
              tick={{ fill: AXIS_TEXT, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f5f5f4' }} />
            <Bar
              dataKey="co2_kg"
              barSize={16}
              radius={[0, 4, 4, 0]}
              minPointSize={3}
              isAnimationActive={false}
            >
              {/* A bar of a few pixels and a value label keep 0 kg (the bike) visible. */}
              <LabelList
                dataKey="co2_kg"
                position="right"
                formatter={formatCo2Label}
                fill={AXIS_TEXT}
                fontSize={12}
              />
              {rows.map((row) => (
                <Cell key={row.mode} fill={MODE_CHART_COLORS[row.mode]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>CO₂ footprint by transport mode, kg per person</caption>
        <thead>
          <tr>
            <th scope="col">Mode</th>
            <th scope="col">CO₂ footprint</th>
            <th scope="col">Trips</th>
            <th scope="col">Distance</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.mode}>
              <th scope="row">{row.label}</th>
              <td>{formatCo2(row.co2_kg)}</td>
              <td>{row.trips}</td>
              <td>{formatDistance(row.distance_km)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
