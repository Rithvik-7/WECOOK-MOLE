const OUTBOX = "mole-sos-outbox-v1";

export function readOutbox(storage) {
  try {
    const rows = JSON.parse(storage.getItem(OUTBOX));
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

export function queueSOS(storage, packet) {
  const rows = readOutbox(storage);
  if (!rows.some((row) => row.packet?.request_id === packet.request_id)) {
    rows.push({ packet, createdAt: new Date().toISOString(), status: "LOCAL_PENDING" });
  }
  storage.setItem(OUTBOX, JSON.stringify(rows));
  return rows;
}

export function cancelLocal(storage, requestId) {
  const rows = readOutbox(storage).map((row) =>
    row.packet?.request_id === requestId && row.status === "LOCAL_PENDING" ? { ...row, status: "CANCELLED" } : row,
  );
  storage.setItem(OUTBOX, JSON.stringify(rows));
  return rows;
}

export async function flushSOS(storage, send) {
  for (const item of readOutbox(storage).filter((row) => row.status === "LOCAL_PENDING")) {
    try {
      const receipt = await send(item.packet);
      if (!receipt?.id || !receipt?.status) throw new Error("Server receipt is incomplete");
      const latest = readOutbox(storage).map((row) =>
        row.packet?.request_id === item.packet.request_id
          ? { requestId: item.packet.request_id, createdAt: row.createdAt, status: receipt.status, receiptId: receipt.id }
          : row,
      );
      storage.setItem(OUTBOX, JSON.stringify(latest));
    } catch (error) {
      return { items: readOutbox(storage), error: error.message };
    }
  }
  return { items: readOutbox(storage), error: null };
}
