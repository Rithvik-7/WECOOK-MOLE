import { useEffect, useMemo, useState } from "react";
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { cancelLocal, flushSOS, queueSOS, readOutbox } from "./src/outbox";
import { conditionLabel, copy, createSos, recordNotice, requestId, siteCondition, statusText, visibleAlerts } from "./src/companion";

const DEFAULT_API = process.env.EXPO_PUBLIC_MOLE_API || "http://10.202.0.178:8000";
const KEYS = {
  outbox: "mole-sos-outbox-v1",
  api: "mole-api-base",
  lang: "mole-lang",
  minimum: "mole-minimum",
};
const memory = new Map();
const storage = {
  getItem: (key) => (memory.has(key) ? memory.get(key) : null),
  setItem: (key, value) => {
    memory.set(key, value);
    AsyncStorage.setItem(key, value).catch(() => {});
  },
};

function readingLine(node) {
  const latest = node.latest || {};
  const parts = [];
  if (Number.isFinite(Number(latest.tilt_deg))) parts.push(`Tilt ${Number(latest.tilt_deg).toFixed(2)}°`);
  if (Number.isFinite(Number(latest.vibration))) parts.push(`Vibration ${Number(latest.vibration).toFixed(2)}`);
  if (Number.isFinite(Number(latest.gas_raw))) parts.push(`Gas ${Math.round(Number(latest.gas_raw))}`);
  if (Number.isFinite(Number(latest.temperature_c))) parts.push(`${Number(latest.temperature_c).toFixed(1)}°C`);
  if (Number.isFinite(Number(latest.humidity_pct))) parts.push(`${Math.round(Number(latest.humidity_pct))}% RH`);
  return parts.join(" · ") || "No reading in this copy";
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("home");
  const [lang, setLang] = useState("en");
  const [apiBase, setApiBase] = useState(DEFAULT_API);
  const [apiDraft, setApiDraft] = useState(DEFAULT_API);
  const [state, setState] = useState(null);
  const [savedAt, setSavedAt] = useState(null);
  const [offline, setOffline] = useState(false);
  const [armed, setArmed] = useState(false);
  const [landmark, setLandmark] = useState("");
  const [message, setMessage] = useState("");
  const [outbox, setOutbox] = useState([]);
  const [notices, setNotices] = useState([]);
  const [minimum, setMinimum] = useState("watch");
  const text = copy[lang];
  const nodes = state?.nodes || [];
  const condition = siteCondition(nodes);
  const alerts = useMemo(() => visibleAlerts(state?.incidents || [], minimum), [state, minimum]);
  const missions = state?.missions || [];

  useEffect(() => {
    let alive = true;
    AsyncStorage.multiGet([KEYS.outbox, KEYS.api, KEYS.lang, KEYS.minimum]).then((pairs) => {
      if (!alive) return;
      const saved = Object.fromEntries(pairs);
      if (saved[KEYS.outbox]) memory.set(KEYS.outbox, saved[KEYS.outbox]);
      setOutbox(readOutbox(storage));
      const base = saved[KEYS.api] || DEFAULT_API;
      setApiBase(base);
      setApiDraft(base);
      if (saved[KEYS.lang] === "hi" || saved[KEYS.lang] === "en") setLang(saved[KEYS.lang]);
      if (saved[KEYS.minimum] === "watch" || saved[KEYS.minimum] === "movement") setMinimum(saved[KEYS.minimum]);
      setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  async function refresh(base = apiBase) {
    try {
      const response = await fetch(`${base.replace(/\/$/, "")}/api/state`);
      if (!response.ok) throw new Error("unavailable");
      const body = await response.json();
      setState(body);
      setSavedAt(new Date().toISOString());
      setOffline(false);
      setNotices((history) => (body.incidents || []).filter((item) => item.status !== "CLOSED").reduce(recordNotice, history));
      const flushed = await flushSOS(storage, async (packet) => {
        const sent = await fetch(`${base.replace(/\/$/, "")}/api/sos`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(packet),
        });
        if (!sent.ok) throw new Error("not delivered");
        return sent.json();
      });
      setOutbox(flushed.items);
    } catch {
      setOffline(true);
    }
  }

  useEffect(() => {
    if (ready) refresh(apiBase);
  }, [ready]);

  function send() {
    const packet = createSos({ requestId: requestId(), landmark, message, lat: null, lon: null });
    setOutbox(queueSOS(storage, packet));
    setArmed(false);
    setLandmark("");
    setMessage("");
    refresh();
  }

  function chooseLanguage() {
    const next = lang === "en" ? "hi" : "en";
    setLang(next);
    storage.setItem(KEYS.lang, next);
  }

  function chooseMinimum() {
    const next = minimum === "watch" ? "movement" : "watch";
    setMinimum(next);
    storage.setItem(KEYS.minimum, next);
  }

  function saveServer() {
    const next = apiDraft.trim() || DEFAULT_API;
    setApiBase(next);
    setApiDraft(next);
    storage.setItem(KEYS.api, next);
    refresh(next);
  }

  return (
    <SafeAreaView style={styles.screen}>
      <Text style={styles.brand}>MOLE</Text>
      <ScrollView contentContainerStyle={styles.body}>
        {tab === "home" && (
          <View>
            <Text style={styles.title}>{state?.site?.name || text.site}</Text>
            <Text style={styles.condition}>{conditionLabel(condition, lang)}</Text>
            <Text style={styles.muted}>{alerts[0]?.title || alerts[0]?.explanation || text.noGps}</Text>
            <Text style={styles.muted}>
              {alerts.length} open · {missions.length} rover mission{missions.length === 1 ? "" : "s"}
            </Text>
            <Text style={styles.muted}>{offline ? `${text.offlineAge}: ${savedAt || "—"}` : savedAt || "—"}</Text>
            <Pressable style={styles.button} onPress={() => refresh()}><Text style={styles.buttonText}>Refresh</Text></Pressable>
            {alerts.slice(0, 3).map((item) => (
              <View key={item.id} style={styles.card}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.muted}>{conditionLabel(item.severity, lang)} · {item.status}</Text>
              </View>
            ))}
          </View>
        )}
        {tab === "alerts" && (
          <View>
            <Text style={styles.title}>{text.alerts}</Text>
            <Text style={styles.muted}>{text.push}</Text>
            {alerts.length === 0 && notices.length === 0 && <Text style={styles.muted}>No in-app notices yet.</Text>}
            {alerts.map((item) => (
              <View key={item.id} style={styles.card}>
                <Text style={styles.cardTitle}>{item.title}</Text>
                <Text style={styles.muted}>{conditionLabel(item.severity, lang)} · {item.status}</Text>
              </View>
            ))}
            {notices.map((item) => (
              <View key={`${item.id}-${item.severity}`} style={styles.card}>
                <Text style={styles.cardTitle}>{conditionLabel(item.severity, lang)}</Text>
                <Text style={styles.muted}>{item.state} · {item.at || "—"}</Text>
              </View>
            ))}
            {outbox.map((item) => (
              <View key={item.requestId || item.packet?.request_id} style={styles.card}>
                <Text style={styles.cardTitle}>{text.sos}</Text>
                <Text style={styles.muted}>{statusText(item.status, lang)}</Text>
                {item.packet?.landmark ? <Text style={styles.muted}>{item.packet.landmark}</Text> : null}
              </View>
            ))}
          </View>
        )}
        {tab === "map" && (
          <View>
            <Text style={styles.title}>{text.map}</Text>
            <Text style={styles.muted}>{text.offlineAge}: {savedAt || "—"}</Text>
            {nodes.map((node) => (
              <View key={node.id} style={styles.card}>
                <Text style={styles.cardTitle}>{node.name || node.id}</Text>
                <Text style={styles.muted}>{conditionLabel(node.condition, lang)} · {node.place}</Text>
                <Text style={styles.muted}>{readingLine(node)}</Text>
                {node.analysis?.summary ? <Text style={styles.muted}>{node.analysis.summary}</Text> : null}
              </View>
            ))}
          </View>
        )}
        {tab === "more" && (
          <View>
            <Text style={styles.title}>{text.more}</Text>
            <Pressable style={styles.button} onPress={chooseLanguage}><Text style={styles.buttonText}>{lang === "en" ? "हिन्दी" : "English"}</Text></Pressable>
            <Pressable style={styles.button} onPress={chooseMinimum}><Text style={styles.buttonText}>{minimum === "watch" ? text.watch : text.movement}</Text></Pressable>
            <Text style={styles.muted}>Server address</Text>
            <TextInput
              style={styles.input}
              value={apiDraft}
              onChangeText={setApiDraft}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder="http://192.168.0.10:8000"
              placeholderTextColor="#8e887c"
            />
            <Pressable style={styles.button} onPress={saveServer}><Text style={styles.buttonText}>Save server</Text></Pressable>
            <Text style={styles.muted}>{text.sms}</Text>
            <Text style={styles.muted}>{text.push}</Text>
          </View>
        )}
        {tab === "sos" && (
          <View>
            <Text style={styles.title}>{text.sos}</Text>
            <Text style={styles.muted}>{text.noGps}</Text>
            <TextInput style={styles.input} value={landmark} onChangeText={setLandmark} placeholder="Landmark" placeholderTextColor="#8e887c" />
            <TextInput style={styles.input} value={message} onChangeText={setMessage} placeholder="Message" placeholderTextColor="#8e887c" />
            {!armed ? (
              <Pressable style={styles.critical} onPress={() => setArmed(true)}><Text style={styles.buttonText}>{text.prepare}</Text></Pressable>
            ) : (
              <Pressable style={styles.critical} onPress={send}><Text style={styles.buttonText}>{text.send}</Text></Pressable>
            )}
            <Pressable style={styles.button} onPress={() => { setArmed(false); const pending = readOutbox(storage).find((item) => item.status === "LOCAL_PENDING"); if (pending) setOutbox(cancelLocal(storage, pending.packet.request_id)); }}><Text style={styles.buttonText}>{text.cancel}</Text></Pressable>
          </View>
        )}
      </ScrollView>
      <View style={styles.nav}>
        {["home", "alerts", "map", "more"].map((item) => (
          <Pressable key={item} style={styles.navItem} onPress={() => setTab(item)}><Text style={tab === item ? styles.navOn : styles.navOff}>{text[item]}</Text></Pressable>
        ))}
      </View>
      <Pressable style={styles.sosBar} onPress={() => setTab("sos")}><Text style={styles.buttonText}>{text.sos}</Text></Pressable>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#050506" },
  body: { padding: 20, paddingBottom: 120 },
  brand: { color: "#f7f1de", fontSize: 18, letterSpacing: 3, paddingHorizontal: 20, paddingTop: 8 },
  title: { color: "#f7f1de", fontSize: 28, marginVertical: 8 },
  condition: { color: "#f7f1de", fontSize: 20, marginBottom: 8 },
  muted: { color: "rgba(247,241,222,0.72)", fontSize: 16, lineHeight: 22, marginBottom: 8 },
  card: { backgroundColor: "#1c1c1e", borderColor: "rgba(255,255,255,0.14)", borderWidth: 1, borderRadius: 18, padding: 14, marginVertical: 6 },
  cardTitle: { color: "#f7f1de", fontSize: 16 },
  button: { minHeight: 48, borderRadius: 14, backgroundColor: "#2a2a2e", alignItems: "center", justifyContent: "center", marginVertical: 6 },
  critical: { minHeight: 52, borderRadius: 14, backgroundColor: "#8e1b2c", alignItems: "center", justifyContent: "center", marginVertical: 8 },
  buttonText: { color: "#f7f1de", fontSize: 16 },
  input: { minHeight: 48, borderRadius: 14, backgroundColor: "#1c1c1e", color: "#f7f1de", paddingHorizontal: 12, marginVertical: 6, borderWidth: 1, borderColor: "rgba(255,255,255,0.14)" },
  nav: { position: "absolute", left: 12, right: 12, bottom: 64, height: 58, borderRadius: 20, backgroundColor: "#1c1c1e", flexDirection: "row", alignItems: "center", justifyContent: "space-around", borderWidth: 1, borderColor: "rgba(255,255,255,0.14)" },
  navItem: { minWidth: 64, minHeight: 44, alignItems: "center", justifyContent: "center" },
  navOn: { color: "#f7f1de" },
  navOff: { color: "rgba(247,241,222,0.55)" },
  sosBar: { position: "absolute", left: 12, right: 12, bottom: 12, minHeight: 44, borderRadius: 14, backgroundColor: "#8e1b2c", alignItems: "center", justifyContent: "center" },
});
