import type { TransportMode } from '@/types/trip';

/** Chart colours per mode: the 600 step of the hue used by `ModeBadge`. Charts always label
 * modes in text as well, so colour is never the only cue. */
export const MODE_CHART_COLORS: Record<TransportMode, string> = {
  car_petrol: '#ea580c', // orange-600
  car_ev: '#0284c7', // sky-600
  train: '#059669', // emerald-600
  coach: '#0d9488', // teal-600
  plane: '#e11d48', // rose-600
  bike: '#65a30d', // lime-600
};
