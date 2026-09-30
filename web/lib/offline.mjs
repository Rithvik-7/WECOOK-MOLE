const SNAPSHOT = "mole-snapshot-v1";
const OUTBOX = "mole-sos-outbox-v1";
export function readSnapshot(storage) {
  try {
    const x = JSON.parse(storage.getItem(SNAPSHOT));
    return x?.data?.nodes && x?.savedAt ? x : null;
  } catch {
    return null;
  }
}
export function saveSnapshot(storage, data) {
  const snapshot = {
    savedAt: new Date().toISOString(),
    data: {
      site: data.site,
      nodes: data.nodes,
      incidents: data.incidents,
      missions: [],
      sos: [],
      weather: data.weather,
      model_state: data.model_state,
    },
  };
  storage.setItem(SNAPSHOT, JSON.stringify(snapshot));
  return snapshot;
}
export function readOutbox(storage) {
  try {
    const x = JSON.parse(storage.getItem(OUTBOX));
    return Array.isArray(x) ? x : [];
  } catch {
    return [];
  }
}
export function queueSOS(storage, packet) {
  const rows = readOutbox(storage);
  if (!rows.some((x) => x.packet?.request_id === packet.request_id))
    rows.push({
      packet,
      createdAt: new Date().toISOString(),
      status: "LOCAL_PENDING",
    });
  storage.setItem(OUTBOX, JSON.stringify(rows));
  return rows;
}
export async function flushSOS(storage, send) {
  // Commit one receipt at a time; server deduplicates retry after a lost response.
  for (const item of readOutbox(storage).filter(
    (x) => x.status === "LOCAL_PENDING",
  )) {
    try {
      const receipt = await send(item.packet);
      if (!receipt.id || !receipt.status)
        throw new Error("Server receipt is incomplete");
      const latest = readOutbox(storage).map((x) =>
        x.packet?.request_id === item.packet.request_id
          ? {
              requestId: item.packet.request_id,
              createdAt: x.createdAt,
              status: receipt.status,
              receiptId: receipt.id,
            }
          : x,
      );
      storage.setItem(OUTBOX, JSON.stringify(latest));
    } catch (error) {
      return { items: readOutbox(storage), error: error.message };
    }
  }
  return { items: readOutbox(storage), error: null };
}
export function updateReceipts(storage, statuses) {
  const byId=new Map(statuses.map(x=>[x.id,x.status]));
  const rows=readOutbox(storage).map(x=>byId.has(x.receiptId)?{...x,status:byId.get(x.receiptId)}:x);
  storage.setItem(OUTBOX,JSON.stringify(rows));return rows;
}
