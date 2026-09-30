import Link from "next/link";
export default function Offline() {
  return (
    <main className="safety-shell">
      <p className="eyebrow">MOLE / OFFLINE</p>
      <h1>The connection is unavailable.</h1>
      <p>
        Previously visited pages may still open. Cached readings are historical
        observations, not live conditions. SOS requests saved on this device
        need connectivity to reach the server.
      </p>
      <Link className="button primary" href="/safety">
        Open field companion
      </Link>
      <a className="button" href="/">
        Retry workspace
      </a>
    </main>
  );
}
