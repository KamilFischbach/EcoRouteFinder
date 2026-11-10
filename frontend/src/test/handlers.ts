import { http, HttpResponse } from 'msw';

import { API_URL } from '@/api/client';
import type { Comparison, ComparisonOption } from '@/types/comparison';
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
  route: {
    origin: { name: 'Warszawa', lat: 52.2334, lon: 21.0711 },
    destination: { name: 'Kraków', lat: 50.0469, lon: 19.9972 },
    distance_km: 299.5,
    source: 'osrm',
  },
  passengers: 2,
  options: [
    option('bike', 305.3, 1221, 0, 0, 48.37, false, 'Too far to cycle (over 100 km).'),
    option('train', 305.3, 219, 91.58, 9.44, 38.93, true),
    option('coach', 299.5, 272, 53.9, 11.82, 36.55, true),
    option('car_ev', 299.5, 211, 37.43, 16.92, 31.45, true),
    option('car_petrol', 299.5, 211, 67.38, 24.18, 24.19, true),
    option('plane', 254.4, 151, 203.52, 58.33, -9.96, false, 'Not worth flying under 300 km.'),
  ],
  highlights: { greenest: 'train', fastest: 'car_ev', cheapest: 'car_ev' },
};

function option(
  mode: TransportMode,
  distance_km: number,
  duration_min: number,
  cost_pln: number,
  co2_kg: number,
  co2_saved_vs_car_kg: number,
  practical: boolean,
  note: string | null = null,
): ComparisonOption {
  return {
    mode,
    distance_km,
    duration_min,
    cost_pln,
    co2_kg,
    co2_saved_vs_car_kg,
    practical,
    note,
  };
}

export const handlers = [
  http.post(`${API_URL}/comparisons`, () => HttpResponse.json(comparisonFixture)),

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
