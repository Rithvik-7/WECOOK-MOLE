import assert from "node:assert/strict";
import { cancelLocal, flushSOS, queueSOS, readOutbox } from "../mobile/src/outbox.js";
import { createSos, recordNotice, requestId, siteCondition, statusText, visibleAlerts } from "../mobile/src/companion.js";

function memory() {
  const data = new Map();
  return { getItem: (key) => (data.has(key) ? data.get(key) : null), setItem: (key, value) => data.set(key, value) };
}

const store = memory();
const packet = createSos({ requestId: "11111111-1111-4111-8111-111111111111", landmark: "north road", message: "need help" });
assert.equal(packet.lat, null);
assert.equal(packet.delivered, false);
queueSOS(store, packet);
assert.equal(readOutbox(store)[0].status, "LOCAL_PENDING");
assert.equal(statusText("LOCAL_PENDING", "hi").includes("नहीं"), true);

const failed = await flushSOS(store, async () => { throw new Error("offline"); });
assert.equal(failed.error, "offline");
assert.equal(readOutbox(store)[0].status, "LOCAL_PENDING");

const sent = await flushSOS(store, async () => ({ id: "SOS-1", status: "QUEUED" }));
assert.equal(sent.items[0].status, "QUEUED");
assert.equal(sent.items[0].receiptId, "SOS-1");
const again = await flushSOS(store, async () => { throw new Error("should not resend"); });
assert.equal(again.error, null);

const second = createSos({ requestId: "22222222-2222-4222-8222-222222222222", message: "mistake" });
queueSOS(store, second);
cancelLocal(store, second.request_id);
assert.equal(readOutbox(store).find((row) => row.packet?.request_id === second.request_id).status, "CANCELLED");

const nodes = [{ condition: "normal" }, { condition: "movement" }];
assert.equal(siteCondition(nodes), "movement");
const alerts = visibleAlerts([{ id: "a", status: "OPEN", severity: "watch" }, { id: "b", status: "OPEN", severity: "movement" }], "movement");
assert.deepEqual(alerts.map((item) => item.id), ["b"]);
const once = recordNotice([], { id: "a", severity: "movement", updated_at: "t" });
assert.equal(recordNotice(once, { id: "a", severity: "movement" }).length, 1);
assert.equal(statusText("QUEUED").includes("person"), true);
assert.match(requestId(), /^[a-f0-9-]{36}$/);

console.log("stage 7 ok");
