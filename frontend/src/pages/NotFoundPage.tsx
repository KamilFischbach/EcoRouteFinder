import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="py-20 text-center">
      <p className="text-sm font-semibold text-emerald-600">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-stone-900">Nie ma takiej strony</h1>
      <Link
        to="/"
        className="mt-6 inline-block text-sm font-medium text-emerald-700 hover:underline"
      >
        Wróć do tras
      </Link>
    </div>
  );
}
