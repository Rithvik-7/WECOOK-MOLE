"use client";

export function SystemHealth({ items }) {
  return (
    <section className="health-bar" aria-label="System health">
      <strong>System health</strong>
      <ul>
        {items.map((item) => (
          <li key={item.label} data-ok={item.ok ? "yes" : "no"}>
            <span aria-hidden="true">{item.ok ? "✓" : "–"}</span>
            {item.label}
          </li>
        ))}
      </ul>
    </section>
  );
}
