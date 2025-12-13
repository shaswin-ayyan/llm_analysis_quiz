// @ts-check
import { createExecutionContext, env, waitOnExecutionContext } from "cloudflare:test";
import { it, vi } from "vitest";

const BASE = "https://example.com";

export const makeStory = (worker) => (title, script) =>
  it(title, async () => {
    const scene = stage(worker);
    await script(scene);
  });

export const resetStage = () => {
  vi.restoreAllMocks();
  vi.useRealTimers();
};

export function stage(worker) {
  const assets = stubAssets();
  const db = fakeDb();
  const overrides = { ASSETS: assets, tds_llm_analysis: db };

  const world = {
    assets,
    db,
    at(iso) {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(iso));
      return world;
    },
    link(path, params = {}) {
      const url = new URL(path, BASE);
      const query = new URLSearchParams(params);
      if ([...query].length) url.search = query.toString();
      return url.toString();
    },
    withParent(row) {
      return db.seed(row);
    },
    breakDb(message = "oops") {
      db.fail(new Error(message));
      return world;
    },
    async get(path, init) {
      return world.request(path, { method: "GET", ...init });
    },
    async post(path, init = {}) {
      return world.request(path, { method: "POST", ...init });
    },
    async submit(update) {
      const form = defaultPayload();
      update?.(form);
      return world.post("/submit", { body: JSON.stringify(form) });
    },
    async request(path, init = {}) {
      const ctx = createExecutionContext();
      const response = await worker.fetch(buildRequest(path, init), wrapEnv(overrides), ctx);
      await waitOnExecutionContext(ctx);
      return response;
    },
    json: (response) => response.clone().json(),
    text: (response) => response.clone().text(),
  };

  return world;
}

const defaultPayload = () => ({
  email: "alice@example.com",
  secret: "s3cret",
  url: `${BASE}/demo`,
  answer: "ready",
});

function buildRequest(path, init) {
  const { raw, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (!headers.has("CF-Connecting-IP")) headers.set("CF-Connecting-IP", "203.0.113.10");
  if (!raw && typeof rest.body === "string" && rest.body.trim().startsWith("{") && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return new Request(new URL(path, BASE), { ...rest, headers });
}

const wrapEnv = (overrides) =>
  new Proxy(env, {
    get(target, key) {
      return key in overrides ? overrides[key] : target[key];
    },
  });

function stubAssets() {
  const routes = new Map();
  const hits = [];
  const fetch = vi.fn(async (input) => {
    const path = pathOf(input);
    hits.push(path);
    const handler = routes.get(path) ?? routes.get("*");
    return handler ? handler() : new Response("", { status: 404 });
  });
  return {
    fetch,
    serve(text) {
      routes.set("*", () => new Response(text));
      return this;
    },
    file(path, text) {
      routes.set(path, () => new Response(text));
      return this;
    },
    requests: () => [...hits],
  };
}

const pathOf = (input) => new URL(input instanceof Request ? input.url : input, BASE).pathname;

function fakeDb(seed = []) {
  const rows = seed.map((row) => ({ ...row }));
  const updates = [];
  let failure = null;
  let nextId = rows.reduce((max, row) => Math.max(max, row.id ?? 0), 0) + 1;
  let inserted = null;

  const ensure = () => {
    if (failure) throw failure;
  };

  return {
    seed(row) {
      const copy = { ...row };
      if (copy.id == null) copy.id = nextId++;
      nextId = Math.max(nextId, copy.id + 1);
      rows.push(copy);
      return copy;
    },
    fail(error) {
      failure = error;
    },
    inserted: () => inserted,
    updated: () => updates.at(-1),
    prepare(sql) {
      let values = [];
      return {
        bind(...args) {
          values = args;
          return this;
        },
        async run() {
          ensure();
          if (/INSERT INTO submit/i.test(sql)) {
            const [timestamp, ip, email, secret, url, answer] = values;
            inserted = { id: nextId++, timestamp, ip, email, secret, url, answer };
            rows.push(inserted);
            return { meta: { last_row_id: inserted.id } };
          }
          if (/UPDATE submit/i.test(sql)) {
            const [correct, reason, delay, nextUrl, id] = values;
            const target = rows.find((row) => row.id === Number(id));
            if (target) Object.assign(target, { correct, reason, delay, next_url: nextUrl });
            const change = { id: Number(id), correct, reason, delay, next_url: nextUrl };
            updates.push(change);
            return { meta: {} };
          }
          throw new Error(`Unsupported SQL run: ${sql}`);
        },
        async all() {
          ensure();
          if (/SELECT \* FROM submit/i.test(sql)) {
            const [id] = values;
            return { results: rows.filter((row) => row.id === Number(id)) };
          }
          throw new Error(`Unsupported SQL all: ${sql}`);
        },
      };
    },
  };
}
