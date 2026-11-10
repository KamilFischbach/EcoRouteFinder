import { http, HttpResponse } from 'msw';

import { API_URL } from '@/api/client';
import type { Trip, TripInput } from '@/types/trip';

export const tripFixtures: Trip[] = [
  {
    id: 1,
    origin: 'Warszawa',
    destination: 'Gdańsk',
    distance_km: 340,
    passengers: 2,
    mode: 'train',
    co2_kg: null,
    note: 'Weekend nad morzem',
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

export const handlers = [
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
      error: { code: 'not_found', message: `Trip with id ${String(id)} not found`, details: null },
    },
    { status: 404 },
  );
}
