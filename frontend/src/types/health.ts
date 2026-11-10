// Mirrors backend/app/schemas/health.py.
export interface Health {
  status: string;
  ai_available: boolean;
  ai_model: string | null;
}
