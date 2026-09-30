const glyphs = {
  0: ["01110", "11011", "11011", "11011", "11011", "11011", "01110"],
  1: ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  2: ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
  3: ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  4: ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  5: ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
  6: ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
  7: ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  8: ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  9: ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
  ".": ["0", "0", "0", "0", "0", "1", "1"],
  "+": ["000", "010", "010", "111", "010", "010", "000"],
  "-": ["000", "000", "000", "111", "000", "000", "000"],
};
export function DotNumber({ text, className = "" }) {
  let offset = 0;
  const circles = [];
  for (const char of String(text)) {
    const glyph = glyphs[char] || glyphs["-"];
    glyph.forEach((row, y) =>
      [...row].forEach((v, x) => {
        if (v === "1")
          circles.push(
            <circle
              key={`${offset}-${x}-${y}`}
              cx={offset + x * 4 + 2}
              cy={y * 4 + 2}
              r="1.25"
            />,
          );
      }),
    );
    offset += (glyph[0].length + 1) * 4;
  }
  return (
    <svg
      className={`dot-number ${className}`}
      viewBox={`0 0 ${offset} 28`}
      role="img"
      aria-label={String(text)}
      style={{ width: `${offset / 28}em` }}
      fill="currentColor"
    >
      {circles}
    </svg>
  );
}
export function InstrumentScale() {
  return (
    <svg className="instrument-scale" viewBox="0 0 260 38" aria-hidden="true">
      {Array.from({ length: 43 }, (_, i) => (
        <line
          key={i}
          x1={4 + i * 6}
          x2={4 + i * 6}
          y1={i % 7 === 0 ? 4 : 12}
          y2="27"
          stroke="currentColor"
          opacity={i % 7 === 0 ? 0.65 : 0.22}
        />
      ))}
      <path d="m126 35 4-6 4 6Z" fill="currentColor" />
    </svg>
  );
}
