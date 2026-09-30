export default function manifest() {
  return {
    name: "MOLE Field Companion",
    short_name: "MOLE",
    description: "Monitoring records, alerts and SOS receipts.",
    start_url: "/safety",
    display: "standalone",
    background_color: "#f7f1de",
    theme_color: "#f7f4e9",
    icons: [
      {
        src: "/mole-icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
