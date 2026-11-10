// Small weather glyphs chosen from the WMO weather code (paths adapted from Lucide, ISC licence).

type Kind = 'sun' | 'cloud' | 'rain' | 'snow';

function kindFor(code: number | null): Kind {
  if (code === null) return 'cloud';
  if (code === 0 || code === 1) return 'sun';
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return 'snow';
  if (code >= 51) return 'rain';
  return 'cloud';
}

const CLOUD = 'M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z';

export function WeatherIcon({ code, className }: { code: number | null; className?: string }) {
  const kind = kindFor(code);
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      data-weather={kind}
    >
      {kind === 'sun' && (
        <>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </>
      )}
      {kind === 'cloud' && <path d={CLOUD} />}
      {kind === 'rain' && (
        <>
          <path d="M4 14.9A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.24" />
          <path d="M16 14v6M8 14v6M12 16v6" />
        </>
      )}
      {kind === 'snow' && (
        <>
          <path d="M4 14.9A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.24" />
          <path d="M8 15h.01M8 19h.01M12 17h.01M12 21h.01M16 15h.01M16 19h.01" />
        </>
      )}
    </svg>
  );
}
