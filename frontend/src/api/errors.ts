import { ApiError } from './client';

/** Turns any thrown value into a short, user-facing Polish message. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'network_error':
        return 'Brak połączenia z API. Sprawdź, czy backend działa na porcie 8000.';
      case 'validation_error':
        return 'Serwer odrzucił dane. Sprawdź pola formularza.';
      case 'not_found':
        return 'Nie znaleziono trasy. Mogła zostać usunięta.';
      default:
        return 'Coś poszło nie tak po stronie serwera. Spróbuj ponownie.';
    }
  }
  return 'Wystąpił nieoczekiwany błąd. Spróbuj ponownie.';
}
