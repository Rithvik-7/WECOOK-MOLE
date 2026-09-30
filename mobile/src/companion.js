export const copy = {
  en: {
    home: "Home",
    alerts: "Alerts",
    map: "Map",
    more: "More",
    sos: "SOS",
    site: "East Panel Demonstration",
    prepare: "Prepare SOS",
    send: "Send SOS",
    cancel: "Cancel",
    notDelivered: "This request has not been delivered. It stays on this device.",
    serverReceived: "The server stored this request. That is not confirmation a person has seen it.",
    operatorNoted: "An operator recorded a note. This is not a rescue confirmation.",
    cancelled: "Cancelled before it was sent.",
    push: "Phone push is not configured.",
    sms: "SMS and email are not configured.",
    noGps: "Location is optional. SOS can be sent without it.",
    offlineAge: "Offline copy",
    movement: "Movement alert",
    normal: "Normal",
    watch: "Watch",
    gas: "Gas alert",
    sensor_fault: "Sensor fault",
    stale: "Stale",
    unavailable: "Unavailable",
  },
  hi: {
    home: "होम",
    alerts: "चेतावनियाँ",
    map: "नक्शा",
    more: "और",
    sos: "एसओएस",
    site: "ईस्ट पैनल प्रदर्शन",
    prepare: "एसओएस तैयार करें",
    send: "एसओएस भेजें",
    cancel: "रद्द करें",
    notDelivered: "यह अनुरोध भेजा नहीं गया है। यह इसी उपकरण पर रखा है।",
    serverReceived: "सर्वर ने अनुरोध रख लिया है। इसका अर्थ यह नहीं कि किसी व्यक्ति ने इसे देख लिया है।",
    operatorNoted: "एक ऑपरेटर ने टिप्पणी दर्ज की। यह बचाव की पुष्टि नहीं है।",
    cancelled: "भेजने से पहले रद्द किया गया।",
    push: "फ़ोन पुश सेट नहीं है।",
    sms: "एसएमएस और ईमेल सेट नहीं हैं।",
    noGps: "स्थान वैकल्पिक है। बिना स्थान के भी एसओएस भेजा जा सकता है।",
    offlineAge: "ऑफ़लाइन प्रति",
    movement: "हलचल की चेतावनी",
    normal: "सामान्य",
    watch: "निगरानी",
    gas: "गैस चेतावनी",
    sensor_fault: "सेंसर दोष",
    stale: "पुराना डेटा",
    unavailable: "अनुपलब्ध",
  },
};

const RANK = { normal: 0, unavailable: 1, watch: 2, stale: 3, sensor_fault: 4, gas: 5, movement: 5 };

export function conditionLabel(condition, lang = "en") {
  return copy[lang][condition] || copy[lang].unavailable;
}

export function siteCondition(nodes) {
  return (nodes || []).reduce((best, node) => ((RANK[node.condition] || 0) > (RANK[best] || 0) ? node.condition : best), "unavailable");
}

export function requestId() {
  const bytes = Array.from({ length: 16 }, () => Math.floor(Math.random() * 256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.map((value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function createSos({ requestId, landmark, message, lat, lon, locatedAt }) {
  if (!requestId) throw new Error("SOS needs a request id before it is stored");
  const located = lat != null && lon != null;
  return {
    request_id: requestId,
    landmark: landmark || null,
    message: message || null,
    lat: located ? lat : null,
    lon: located ? lon : null,
    located_at: located ? locatedAt || null : null,
    delivered: false,
  };
}

export function statusText(status, lang = "en") {
  const text = copy[lang];
  if (status === "LOCAL_PENDING") return text.notDelivered;
  if (status === "QUEUED") return text.serverReceived;
  if (status === "ACKNOWLEDGED") return text.operatorNoted;
  if (status === "CANCELLED") return text.cancelled;
  return text.unavailable;
}

export function visibleAlerts(incidents, minimum = "watch") {
  return (incidents || []).filter((item) => item.status !== "CLOSED" && (RANK[item.severity] || 0) >= (RANK[minimum] || 0));
}

export function recordNotice(history, incident) {
  if (!incident?.id) return history;
  if (history.some((item) => item.id === incident.id && item.severity === incident.severity)) return history;
  return [{ id: incident.id, severity: incident.severity, state: "in_app", at: incident.updated_at || null }, ...history];
}
