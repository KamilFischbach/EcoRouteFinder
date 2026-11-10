// Mirrors backend/app/schemas/trip_draft.py.
import type { TransportMode } from './trip';

export type DraftField = 'origin' | 'destination' | 'passengers';

export interface TripDraft {
  origin: string | null;
  destination: string | null;
  passengers: number | null;
  mode: TransportMode | null;
  /** Short English summary of travel needs (luggage, comfort, budget...) for EcoAdvisor. */
  preferences: string | null;
  missing_fields: DraftField[];
  parsed_by: 'llm' | 'rules';
}
