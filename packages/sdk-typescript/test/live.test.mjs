// Integration test against a running API: MESH_URL + MESH_ADMIN_KEY must be set; skipped otherwise.
import { test } from "node:test";
import assert from "node:assert";
import { MemoryMesh } from "../dist/index.js";

const url = process.env.MESH_URL, key = process.env.MESH_ADMIN_KEY;
test("ts sdk round trip", { skip: !url || !key }, async () => {
  const m = new MemoryMesh({ baseUrl: url, apiKey: key });
  const u = "ts_user_" + Date.now();
  await m.events.ingest(u, "I prefer concise answers with numbers.");
  const hits = await m.memory.search(u, "answer style");
  assert.ok(hits.length > 0);
  const c = await m.semantic.compare(u, "professional", ["precision", "formal"]);
  const fb = await m.semantic.feedback(u, c.id, "precision");
  assert.equal(fb.profile.preferred.id, "precision");
  const ctx = await m.context.build(u, "make it more professional");
  assert.ok(ctx.prompt.includes("Factual precision"));
});
