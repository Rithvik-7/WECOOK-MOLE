import Link from "next/link";
export function Brand({ label = "MOLE home" }) {
  return (
    <Link className="brand" href="/" aria-label={label}>
      <span className="brand-word">MOLE</span>
    </Link>
  );
}
