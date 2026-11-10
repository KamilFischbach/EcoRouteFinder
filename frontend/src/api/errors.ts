import { ApiError } from './client';

/** Turns any thrown value into a short, user-facing message. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'network_error':
        return "Can't reach the API. Check that the backend is running on port 8000.";
      case 'validation_error':
        return 'The server rejected the data. Please check the form fields.';
      case 'not_found':
        return 'Trip not found. It may have been deleted.';
      default:
        return 'Something went wrong on the server. Please try again.';
    }
  }
  return 'An unexpected error occurred. Please try again.';
}
