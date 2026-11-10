import { ApiError } from './client';

function placeFromDetails(details: unknown): string | null {
  if (typeof details === 'object' && details !== null && 'place' in details) {
    const { place } = details as { place: unknown };
    return typeof place === 'string' ? place : null;
  }
  return null;
}

/** Turns any thrown value into a short, user-facing message. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'NETWORK_ERROR':
        return "Can't reach the API. Check that the backend is running on port 8000.";
      case 'VALIDATION_ERROR':
        return 'The server rejected the data. Please check the form fields.';
      case 'NOT_FOUND':
        return 'Trip not found. It may have been deleted.';
      case 'UNKNOWN_PLACE': {
        const place = placeFromDetails(error.details);
        return place
          ? `We couldn't find "${place}". Check the spelling or try a nearby town.`
          : "We couldn't find one of the places. Check the spelling.";
      }
      case 'ROUTE_TOO_SHORT':
        return 'Origin and destination are the same place. Pick two different places.';
      case 'SERVICE_UNAVAILABLE':
        return 'The map service is unavailable right now. Try again later, or enter the distance yourself under "Advanced".';
      default:
        return 'Something went wrong on the server. Please try again.';
    }
  }
  return 'An unexpected error occurred. Please try again.';
}
