export function Icon({ name, size = 20, ...props }) {
  const paths = {
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    nodes: (
      <>
        <circle cx="12" cy="5" r="2.5" />
        <circle cx="5" cy="18" r="2.5" />
        <circle cx="19" cy="18" r="2.5" />
        <path d="m11 7-5 8m7-8 5 8M8 18h8" />
      </>
    ),
    analytics: <path d="M3 3v18h18M6 15l4-5 4 3 7-8" />,
    incidents: (
      <>
        <path d="m12 3 10 18H2L12 3Z" />
        <path d="M12 9v5m0 3v.1" />
      </>
    ),
    rover: (
      <>
        <rect x="4" y="8" width="16" height="10" rx="3" />
        <path d="M12 8V4m-3 0h6M8 12v2m8-2v2M6 18v3m12-3v3" />
      </>
    ),
    assistant: (
      <>
        <path d="M21 11a8 8 0 0 1-8 8H7l-4 3V7a4 4 0 0 1 4-4h8a6 6 0 0 1 6 6" />
        <path d="M7 8h8M7 12h5" />
      </>
    ),
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    northeast: <path d="M6 18 18 6M6 6h12v12" />,
    chevron: <path d="m9 5 7 7-7 7" />,
    down: <path d="m6 9 6 6 6-6" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    download: <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />,
    refresh: <path d="M20 8a8 8 0 1 0 0 8M20 3v6h-6" />,
    layers: <path d="m12 3 10 5-10 5L2 8l10-5Zm-9 10 9 5 9-5M3 18l9 4 9-4" />,
    expand: <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />,
    location: (
      <>
        <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" />
        <circle cx="12" cy="10" r="2" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    signal: <path d="M4 18v3m5-7v7m5-12v12m5-17v17" />,
    shield: (
      <>
        <path d="m12 2 8 3v7c0 5-8 10-8 10S4 17 4 12V5l8-3Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    pause: <path d="M8 5v14M16 5v14" />,
    play: <path d="m7 4 14 8-14 8V4Z" />,
    temperature: (
      <>
        <path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z" />
        <path d="M12 8v9" />
      </>
    ),
    drop: <path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z" />,
    wind: <path d="M3 8h12a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h5" />,
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6m0-10v.1" />
      </>
    ),
    document: <path d="M14 2H5v20h14V7l-5-5Zm0 0v5h5M8 12h8M8 16h6" />,
    camera: (
      <>
        <path d="m8 4-2 3H3v14h18V7h-3l-2-3H8Z" />
        <circle cx="12" cy="13" r="4" />
      </>
    ),
    search: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="m15 15 6 6" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    minus: <path d="M5 12h14" />,
    settings: (
      <>
        <path d="M4 6h16M4 12h16M4 18h16" />
        <circle cx="9" cy="6" r="2" />
        <circle cx="16" cy="12" r="2" />
        <circle cx="8" cy="18" r="2" />
      </>
    ),
    calibrate: (
      <>
        <circle cx="12" cy="12" r="7" />
        <circle cx="12" cy="12" r="2" />
        <path d="M12 2v3m0 14v3M2 12h3m14 0h3" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.info}
    </svg>
  );
}
