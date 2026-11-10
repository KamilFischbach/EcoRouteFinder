import { http, HttpResponse } from 'msw';

import { API_URL } from '@/api/client';
import type {
  Advice,
  Comparison,
  ComparisonInput,
  ComparisonOption,
  ComparisonSummary,
} from '@/types/comparison';
import type { TransportMode, Trip, TripInput } from '@/types/trip';

export const tripFixtures: Trip[] = [
  {
    id: 1,
    origin: 'Warszawa',
    destination: 'Gdańsk',
    distance_km: 340,
    passengers: 2,
    mode: 'train',
    co2_kg: null,
    note: 'Weekend by the sea',
    created_at: '2026-11-08T10:00:00Z',
    updated_at: '2026-11-08T10:00:00Z',
  },
  {
    id: 2,
    origin: 'Kraków',
    destination: 'Zakopane',
    distance_km: 110,
    passengers: 4,
    mode: 'car_ev',
    co2_kg: null,
    note: null,
    created_at: '2026-11-09T08:30:00Z',
    updated_at: '2026-11-09T08:30:00Z',
  },
];

// In-memory "database" shared by the handlers; reset after every test in setup.ts.
let trips: Trip[] = [];
let nextId = 1;

export function resetTripDb(initial: Trip[] = tripFixtures): void {
  trips = structuredClone(initial);
  nextId = Math.max(0, ...trips.map((trip) => trip.id)) + 1;
}

export function getTripDb(): readonly Trip[] {
  return trips;
}

// Shaped like a real Warszawa -> Kraków response for 2 passengers.
export const comparisonFixture: Comparison = {
  id: 1,
  created_at: '2026-11-10T10:00:00Z',
  advice: null,
  route: {
    origin: { name: 'Warszawa', lat: 52.2334, lon: 21.0711 },
    destination: { name: 'Kraków', lat: 50.0469, lon: 19.9972 },
    distance_km: 299.5,
    source: 'osrm',
  },
  passengers: 2,
  options: [
    // Savings are per person vs the same 2 people going by petrol car (24.18 kg each).
    option('bike', 305.3, 1221, 0, 0, 24.18, false, 'Too far to cycle (over 100 km).'),
    option('train', 305.3, 219, 91.58, 9.44, 14.74, true),
    option('coach', 299.5, 272, 53.9, 11.82, 12.36, true),
    option('car_ev', 299.5, 211, 37.43, 16.92, 7.26, true),
    option('car_petrol', 299.5, 211, 67.38, 24.18, 0, true),
    option('plane', 254.4, 151, 203.52, 58.33, -34.15, false, 'Not worth flying under 300 km.'),
  ],
  highlights: { greenest: 'train', fastest: 'car_ev', cheapest: 'car_ev' },
};

function option(
  mode: TransportMode,
  distance_km: number,
  duration_min: number,
  cost_pln: number,
  co2_kg: number,
  co2_saved_vs_petrol_car_kg: number,
  practical: boolean,
  note: string | null = null,
): ComparisonOption {
  return {
    mode,
    distance_km,
    duration_min,
    cost_pln,
    co2_kg,
    co2_saved_vs_petrol_car_kg,
    practical,
    note,
  };
}

// Saved comparisons ("database" for the comparison handlers). Empty by default.
let comparisons: Comparison[] = [];

export function resetComparisonDb(initial: Comparison[] = []): void {
  comparisons = structuredClone(initial);
}

export function getComparisonDb(): readonly Comparison[] {
  return comparisons;
}

/** A saved comparison based on the fixture, with its own id, date and route names. */
export function savedComparison(
  id: number,
  createdAt: string,
  origin = 'Warszawa',
  destination = 'Kraków',
): Comparison {
  return {
    ...structuredClone(comparisonFixture),
    id,
    created_at: createdAt,
    route: {
      ...comparisonFixture.route,
      origin: { ...comparisonFixture.route.origin, name: origin },
      destination: { ...comparisonFixture.route.destination, name: destination },
    },
  };
}

export const adviceFixture: Advice = {
  recommended_mode: 'coach',
  summary: 'Take the coach: low CO₂ and the cheapest practical option.',
  reasons: ['11.8 kg CO₂ per person', 'About 54 PLN per person'],
  used_llm: true,
  model: 'qwen3:8b',
  weather: {
    location: 'Kraków',
    temperature_c: 2.8,
    precipitation_mm: 0,
    wind_kph: 9,
    weather_code: 3,
    description: 'overcast',
  },
  preferences: null,
  tool_trace: [{ tool: 'get_weather', arguments: { location: 'Kraków' }, ok: true }],
  created_at: '2026-11-10T12:00:00Z',
};

function toSummary(c: Comparison): ComparisonSummary {
  const greenest = c.options.find((o) => o.mode === c.highlights.greenest) ?? null;
  const first = c.options[0];
  return {
    id: c.id,
    origin: c.route.origin.name,
    destination: c.route.destination.name,
    passengers: c.passengers,
    distance_km: c.route.distance_km,
    created_at: c.created_at,
    greenest_mode: greenest?.mode ?? null,
    greenest_co2_kg: greenest?.co2_kg ?? null,
    petrol_car_co2_kg: first ? first.co2_kg + first.co2_saved_vs_petrol_car_kg : 0,
    recommended_mode: c.advice?.recommended_mode ?? null,
  };
}

export const handlers = [
  http.post(`${API_URL}/trip-drafts`, () =>
    HttpResponse.json({
      origin: 'Gdynia',
      destination: 'Toruń',
      passengers: 2,
      mode: 'train',
      preferences: null,
      missing_fields: [],
      parsed_by: 'llm',
    }),
  ),

  http.get(`${API_URL}/health`, () =>
    HttpResponse.json({ status: 'ok', ai_available: true, ai_model: 'qwen3:8b' }),
  ),

  http.post(`${API_URL}/comparisons`, async ({ request }) => {
    const input = (await request.json()) as ComparisonInput;
    const id = Math.max(0, ...comparisons.map((c) => c.id)) + 1;
    const created = savedComparison(id, new Date().toISOString(), input.origin, input.destination);
    comparisons = [created, ...comparisons];
    return HttpResponse.json(created, { status: 201 });
  }),

  http.get(`${API_URL}/comparisons`, () => HttpResponse.json(comparisons.map(toSummary))),

  http.get(`${API_URL}/comparisons/:id`, ({ params }) => {
    const found = comparisons.find((c) => c.id === Number(params.id));
    return found ? HttpResponse.json(found) : notFound(params.id);
  }),

  http.post(`${API_URL}/comparisons/:id/advice`, async ({ params, request }) => {
    const index = comparisons.findIndex((c) => c.id === Number(params.id));
    const current = comparisons[index];
    if (!current) return notFound(params.id);
    const body = (await request.json()) as { preferences?: string };
    const advice: Advice = { ...adviceFixture, preferences: body.preferences ?? null };
    comparisons[index] = { ...current, advice };
    return HttpResponse.json(advice);
  }),

  http.delete(`${API_URL}/comparisons/:id`, ({ params }) => {
    if (!comparisons.some((c) => c.id === Number(params.id))) return notFound(params.id);
    comparisons = comparisons.filter((c) => c.id !== Number(params.id));
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${API_URL}/trips`, ({ request }) => {
    const mode = new URL(request.url).searchParams.get('mode');
    return HttpResponse.json(mode ? trips.filter((trip) => trip.mode === mode) : trips);
  }),

  http.post(`${API_URL}/trips`, async ({ request }) => {
    const input = (await request.json()) as TripInput;
    const now = new Date().toISOString();
    const trip: Trip = { ...input, id: nextId++, co2_kg: null, created_at: now, updated_at: now };
    trips = [trip, ...trips];
    return HttpResponse.json(trip, { status: 201 });
  }),

  http.put(`${API_URL}/trips/:id`, async ({ params, request }) => {
    const index = trips.findIndex((trip) => trip.id === Number(params.id));
    const current = trips[index];
    if (!current) return notFound(params.id);
    const updated = { ...current, ...((await request.json()) as Partial<TripInput>) };
    trips[index] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete(`${API_URL}/trips/:id`, ({ params }) => {
    const exists = trips.some((trip) => trip.id === Number(params.id));
    if (!exists) return notFound(params.id);
    trips = trips.filter((trip) => trip.id !== Number(params.id));
    return new HttpResponse(null, { status: 204 });
  }),
];

function notFound(id: unknown) {
  return HttpResponse.json(
    {
      error: { code: 'NOT_FOUND', message: `Trip with id ${String(id)} not found`, details: null },
    },
    { status: 404 },
  );
}
