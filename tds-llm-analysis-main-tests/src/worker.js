import { demo2Blob, demo2Key, emailNumber } from "../public/utils.js";

const project2Fixtures = {
  uvFixture: "/project2/uv.json",
  audioPassphrase: ["hushed parrot 219", "hushed parrot two one nine"],
  heatmapHex: "#b45a1e",
  csvNormalized: [
    { id: 1, name: "Alpha", joined: "2024-01-30", value: 5 },
    { id: 2, name: "Gamma", joined: "2024-02-01", value: 7 },
    { id: 3, name: "Beta", joined: "2024-01-02", value: 10 },
  ],
  ghTreeExpected: 1,
  logsSum: 335,
  pdfTotal: 170.97,
  orderLeaders: [
    { customer_id: "B", total: 110 },
    { customer_id: "D", total: 100 },
    { customer_id: "A", total: 90 },
  ],
  chartAnswer: "b",
  shardInputs: {
    dataset: 18000,
    max_docs_per_shard: 3200,
    max_shards: 6,
    min_replicas: 2,
    max_replicas: 3,
    memory_per_shard: 1.5,
    memory_budget: 18,
  },
  embeddingPair: ["s4", "s5"],
  imageDiff: 7,
  rateMinutes: 71,
  ragTop: ["c1", "c2", "c3"],
  f1: { run_id: "runC", macro_f1: 0.8175 },
};

export default {
  async fetch(request, env) {
    try {
      // Any request other than /submit is for a static asset
      const url = new URL(request.url);
      if (url.pathname !== "/submit") return env.ASSETS.fetch(request);

      // /submit only allows POST
      if (request.method !== "POST") return error("Use POST /submit", 405);

      // Parse student JSON submission as `payload`
      let payload;
      try {
        payload = await request.json();
      } catch (e) {
        return error("Body must be valid JSON: " + e.message, 400);
      }

      // payload must have ALL required fields
      for (const field of ["email", "secret", "url", "answer"]) {
        const value = payload[field];
        if (value === undefined || value === null || `${value}`.trim() === "") {
          return error(`Missing field ${field}`, 400);
        }
      }

      // Insert payload immediately into the database before validating
      const query = "INSERT INTO submit (timestamp, ip, email, secret, url, answer) VALUES (?1, ?2, ?3, ?4, ?5, ?6)";
      payload.timestamp = new Date().toISOString();
      payload.ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const answer = typeof payload.answer === "string" ? payload.answer : JSON.stringify(payload.answer);
      const insert = await env.tds_llm_analysis
        .prepare(query)
        .bind(payload.timestamp, payload.ip, payload.email, payload.secret, payload.url, answer)
        .run();
      payload.id = insert.meta.last_row_id;

      // Get parent submission based on ?id=...
      // All payloads (except the student's first) will have a parent, which assigned them the URL.
      // We'll use this to calculate the time delay for submission.
      const parentId = new URL(payload.url).searchParams.get("id") || null;
      let parent = {};
      if (parentId) {
        const query = "SELECT * FROM submit WHERE id = ?1";
        const result = await env.tds_llm_analysis.prepare(query).bind(parentId).all();
        if (!result.results.length) return error(`Invalid id=${parentId}`, 400);
        parent = result.results[0];
      }

      // Validate the answer based on the URL path
      const endpoint = new URL(payload.url).pathname;
      const validator = validators[endpoint];
      if (!validator) return error(`Unknown url: ${payload.url}. Need ${url.origin}/...`, 400);
      const result = await validator({ env, request, origin: url.origin, ...payload });

      // Flag delayed answers, but proceed
      result.delay = null;
      if (parent.timestamp) {
        const start = new Date(parent.timestamp).getTime();
        const end = new Date(payload.timestamp).getTime();
        result.delay = Math.floor((end - start) / 1000);
      }
      const maxDelay = 3 * 60;
      if (result.delay !== null && result.delay > maxDelay) {
        result.correct = false;
        result.reason += ` [DELAY: ${Math.round(result.delay)}s > ${maxDelay}s]`;
      }

      // Update the database with the result
      await env.tds_llm_analysis
        .prepare("UPDATE submit SET correct = ?1, reason = ?2, delay = ?3, next_url = ?4 WHERE id = ?5")
        .bind(result.correct, result.reason, result.delay, result.url, payload.id)
        .run();

      return Response.json(result);
    } catch (e) {
      console.error("Unhandled /submit error", e);
      return error("Internal error: " + e.message, 500);
    }
  },
};

const error = (error, status = 400) => Response.json({ error }, { status });

const validators = {
  "/demo": async ({ origin, email, id, answer }) => {
    const correct = !!answer;
    return {
      correct,
      reason: correct ? "" : "Answer cannot be empty or missing",
      url: `${origin}/demo-scrape?` + new URLSearchParams({ email, id }).toString(),
    };
  },

  "/demo-scrape": async ({ origin, email, id, answer }) => {
    const correct = answer == await emailNumber(email);
    return {
      correct,
      reason: correct ? "" : "Secret mismatch",
      url: `${origin}/demo-audio?` + new URLSearchParams({ email, id }).toString(),
    };
  },

  "/demo-audio": async ({ env, request, email, answer }) => {
    const cutoff = await emailNumber(email);
    const text = await getAsset("demo-audio-data.csv", env, request);
    const numbers = text.trim().split("\n").map(line => parseInt(line));
    const correct = answer == numbers.filter(n => n >= cutoff).reduce((a, b) => a + b, 0);
    return { correct, reason: correct ? "" : "Wrong sum of numbers", url: null };
  },

  "/demo2": async ({ origin, email, id, answer }) => {
    const key = await demo2Key(email);
    const correct = answer === key;
    return {
      correct,
      reason: correct ? "" : "Key mismatch",
      url: `${origin}/demo2-checksum?` + new URLSearchParams({ email, id }).toString(),
    };
  },

  "/demo2-checksum": async ({ email, answer }) => {
    const key = await demo2Key(email);
    const expected = await demo2Checksum(key);
    const correct = answer === expected;
    return { correct, reason: correct ? "" : "Checksum mismatch", url: null };
  },
};

const project2Flow = [
  { path: "/project2", difficulty: 1, next: "/project2-uv", check: checkDemo3Start },
  { path: "/project2-uv", difficulty: 1, next: "/project2-git", check: checkDemo3Uv },
  { path: "/project2-git", difficulty: 1, next: "/project2-md", check: checkDemo3Git },
  { path: "/project2-md", difficulty: 1, next: "/project2-audio-passphrase", check: checkDemo3Markdown },
  { path: "/project2-audio-passphrase", difficulty: 2, next: "/project2-heatmap", check: checkDemo3Audio },
  { path: "/project2-heatmap", difficulty: 2, next: "/project2-csv", check: checkDemo3Heatmap },
  { path: "/project2-csv", difficulty: 2, next: "/project2-gh-tree", check: checkDemo3Csv },
  { path: "/project2-gh-tree", difficulty: 3, next: "/project2-logs", check: checkDemo3GitHubTree },
  { path: "/project2-logs", difficulty: 2, next: "/project2-invoice", check: checkDemo3Logs },
  { path: "/project2-invoice", difficulty: 3, next: "/project2-orders", check: checkDemo3Invoice },
  { path: "/project2-orders", difficulty: 3, next: "/project2-chart", check: checkDemo3Orders },
  { path: "/project2-chart", difficulty: 2, next: "/project2-cache", check: checkDemo3Chart },
  { path: "/project2-cache", difficulty: 3, next: "/project2-shards", check: checkDemo3Cache },
  { path: "/project2-shards", difficulty: 4, next: "/project2-embed", check: checkDemo3Shards },
  { path: "/project2-embed", difficulty: 3, next: "/project2-tools", check: checkDemo3Embeddings },
  { path: "/project2-tools", difficulty: 4, next: "/project2-diff", check: checkDemo3Tools },
  { path: "/project2-diff", difficulty: 3, next: "/project2-rate", check: checkDemo3Diff },
  { path: "/project2-rate", difficulty: 4, next: "/project2-guard", check: checkDemo3Rate },
  { path: "/project2-guard", difficulty: 4, next: "/project2-rag", check: checkDemo3Guard },
  { path: "/project2-rag", difficulty: 5, next: "/project2-f1", check: checkDemo3Rag },
  { path: "/project2-f1", difficulty: 5, next: null, check: checkDemo3F1 },
];

for (const step of project2Flow) {
  validators[step.path] = async ({ origin, email, id, ...rest }) => {
    const { correct, reason } = await step.check({ origin, email, id, ...rest });
    const nextUrl = step.next
      ? `${origin}${step.next}?${new URLSearchParams({ email, id }).toString()}`
      : null;
    return {
      correct,
      reason: reason ?? "",
      url: step.difficulty <= 2 || correct ? nextUrl : null,
    };
  };
}

function checkDemo3Start({ answer }) {
  const ok = !!`${answer}`.trim();
  return { correct: ok, reason: ok ? "" : "Answer cannot be empty" };
}

function checkDemo3Uv({ origin, answer, email }) {
  const fixture = `${origin}${project2Fixtures.uvFixture}`;
  const normalized = `${answer}`.trim();
  const encoded = encodeURIComponent(email ?? "");
  const raw = email ?? "";
  const patterns = [
    new RegExp(
      `uv\\s+http\\s+get\\s+${escapeRegex(fixture)}(?:\\?email=${escapeRegex(encoded)})?.*-h\\s+['\"]?accept:\\s*application/json['\"]?`,
      "i",
    ),
    new RegExp(
      `uv\\s+http\\s+get\\s+${escapeRegex(fixture)}(?:\\?email=${escapeRegex(raw)})?.*-h\\s+['\"]?accept:\\s*application/json['\"]?`,
      "i",
    ),
  ];
  const correct = patterns.some((p) => p.test(normalized));
  return {
    correct,
    reason: correct ? "" : `Submit the command string: uv http get ${fixture}?email=<your email> -H "Accept: application/json"`,
  };
}

function checkDemo3Git({ answer }) {
  const text = `${answer}`.toLowerCase();
  const addIndex = text.search(/git\s+add\s+env\.sample/);
  const commitIndex = text.search(/git\s+commit[^\n]*chore:\s*keep env sample/);
  const correct = addIndex >= 0 && commitIndex > addIndex;
  return { correct, reason: correct ? "" : "Need git add env.sample then git commit -m \"chore: keep env sample\"" };
}

function checkDemo3Markdown({ answer }) {
  const expected = "/project2/data-preparation.md";
  const correct = `${answer}`.trim().toLowerCase() === expected.toLowerCase();
  return { correct, reason: correct ? "" : `Link should be ${expected}` };
}

function checkDemo3Audio({ answer }) {
  const normalized = normalizePassphrase(answer);
  const correct = project2Fixtures.audioPassphrase.some((phrase) => normalized.includes(phrase));
  return { correct, reason: correct ? "" : "Transcribe the spoken phrase (code phrase + digits)" };
}

function checkDemo3Heatmap({ answer }) {
  const normalized = normalizeHex(answer);
  const correct = normalized === project2Fixtures.heatmapHex;
  return { correct, reason: correct ? "" : `Dominant color expected ${project2Fixtures.heatmapHex}` };
}

function checkDemo3Csv({ answer }) {
  const parsed = parseJsonAnswer(answer);
  if (!Array.isArray(parsed)) return { correct: false, reason: "Answer must be a JSON array" };
  const normalized = parsed
    .map((row) => ({
      id: Number(row?.id),
      name: `${row?.name ?? ""}`.trim(),
      joined: `${row?.joined ?? ""}`.trim(),
      value: Number(row?.value),
    }))
    .sort((a, b) => a.id - b.id);
  const allValid = normalized.every((row) => Number.isInteger(row.id) && row.name && row.joined && Number.isInteger(row.value));
  if (!allValid) return { correct: false, reason: "Rows need id, name, joined, value" };
  const correct = JSON.stringify(normalized) === JSON.stringify(project2Fixtures.csvNormalized);
  return { correct, reason: correct ? "" : "Normalized JSON does not match expected output" };
}

function checkDemo3GitHubTree({ answer, email }) {
  const value = toNumber(answer);
  const offset = (email?.length ?? 0) % 2;
  const expected = project2Fixtures.ghTreeExpected + offset;
  const correct = Number.isInteger(value) && value === expected;
  return { correct, reason: correct ? "" : "Count .md files under the given prefix, then add (email length mod 2)" };
}

function checkDemo3Logs({ answer, email }) {
  const value = toNumber(answer);
  const offset = (email?.length ?? 0) % 5;
  const expected = project2Fixtures.logsSum + offset;
  const correct = Number.isFinite(value) && value === expected;
  return { correct, reason: correct ? "" : "Sum download bytes and add the email-length mod 5 offset" };
}

function checkDemo3Invoice({ answer }) {
  const value = toNumber(answer);
  const correct = Number.isFinite(value) && Math.abs(value - project2Fixtures.pdfTotal) < 0.005;
  return { correct, reason: correct ? "" : "Total line items to two decimals" };
}

function checkDemo3Orders({ answer }) {
  const parsed = parseJsonAnswer(answer);
  if (!Array.isArray(parsed)) return { correct: false, reason: "Answer must be a JSON array" };
  const normalized = parsed.map((row) => ({
    customer_id: `${row?.customer_id ?? row?.customerId ?? ""}`.trim().toUpperCase(),
    total: Number(row?.total),
  }));
  const allValid = normalized.every((row) => row.customer_id && Number.isFinite(row.total));
  if (!allValid) return { correct: false, reason: "Provide customer_id and numeric total" };
  const correct = JSON.stringify(normalized) === JSON.stringify(project2Fixtures.orderLeaders);
  return { correct, reason: correct ? "" : "Top 3 running totals do not match" };
}

function checkDemo3Chart({ answer }) {
  const text = `${answer}`.trim().toLowerCase();
  const correct = text === project2Fixtures.chartAnswer || text.includes("stacked");
  return { correct, reason: correct ? "" : "Best pick is stacked area (option B)" };
}

function checkDemo3Cache({ answer }) {
  const text = `${answer}`.toLowerCase();
  const hasCache = /actions\/cache@v4/.test(text);
  const hasPath = /~\/\.npm/.test(text);
  const hasKey = /hashfiles\(['"]\*\*\/package-lock\.json['"]\)/.test(text);
  const hasRestore = /restore-keys/.test(text);
  const correct = hasCache && hasPath && hasKey && hasRestore;
  return { correct, reason: correct ? "" : "Cache ~/.npm with hashFiles(\"**/package-lock.json\") and restore-keys" };
}

function checkDemo3Shards({ answer }) {
  const parsed = parseJsonAnswer(answer);
  if (!parsed || typeof parsed !== "object") return { correct: false, reason: "Answer must be JSON with shards and replicas" };
  const shards = toNumber(parsed.shards);
  const replicas = toNumber(parsed.replicas);
  const constraints = project2Fixtures.shardInputs;
  if (!Number.isInteger(shards) || !Number.isInteger(replicas) || shards <= 0 || replicas <= 0) {
    return { correct: false, reason: "shards and replicas must be positive integers" };
  }
  const docsPerShard = Math.ceil(constraints.dataset / shards);
  const memory = shards * replicas * constraints.memory_per_shard;
  const meetsConstraints =
    shards <= constraints.max_shards &&
    replicas >= constraints.min_replicas &&
    replicas <= constraints.max_replicas &&
    docsPerShard <= constraints.max_docs_per_shard &&
    memory <= constraints.memory_budget;
  const correct = meetsConstraints;
  return { correct, reason: correct ? "" : "Constraints not satisfied for shards/replicas" };
}

function checkDemo3Embeddings({ answer, email }) {
  const ids = parseIdList(answer);
  const evenPair = new Set(project2Fixtures.embeddingPair);
  const oddPair = new Set(["s2", "s3"]);
  const useEven = ((email?.length ?? 0) % 2) === 0;
  const target = useEven ? evenPair : oddPair;
  const correct = ids.length === 2 && ids.every((id) => target.has(id));
  return {
    correct,
    reason: correct ? "" : "If email length is even submit s4,s5; if odd submit s2,s3",
  };
}

function checkDemo3Tools({ answer }) {
  const plan = parseJsonAnswer(answer);
  if (!Array.isArray(plan) || plan.length < 3) return { correct: false, reason: "Provide ordered tool calls as an array" };
  const [first, second, third] = plan;
  const names = plan.map((step) => `${step?.name ?? step?.tool ?? ""}`.toLowerCase());
  const correctOrder = names[0] === "search_docs" && names[1] === "fetch_issue" && names[2] === "summarize";
  const searchArgs = normalizeArgs(first);
  const fetchArgs = normalizeArgs(second);
  const summarizeArgs = normalizeArgs(third);
  const hasQuery = `${searchArgs.query ?? ""}`.toLowerCase();
  const hasIssue = hasQuery.includes("issue 42");
  const hasRepoWords = hasQuery.includes("demo") && hasQuery.includes("api");
  const owner = `${fetchArgs.owner ?? ""}`.toLowerCase();
  const repo = `${fetchArgs.repo ?? ""}`.toLowerCase();
  const id = toNumber(fetchArgs.id);
  const maxTokens = toNumber(summarizeArgs.max_tokens ?? summarizeArgs.maxTokens ?? 0);
  const hasText = !!`${summarizeArgs.text ?? ""}`.trim();
  const correct =
    correctOrder && hasIssue && hasRepoWords && owner === "demo" && repo === "api" && id === 42 && hasText && maxTokens <= 80;
  return { correct, reason: correct ? "" : "Call search_docs -> fetch_issue -> summarize with the provided repo/issue" };
}

function checkDemo3Diff({ answer }) {
  const value = toNumber(answer);
  const correct = Number.isFinite(value) && value === project2Fixtures.imageDiff;
  return { correct, reason: correct ? "" : "Count differing pixels between before.png and after.png" };
}

function checkDemo3Rate({ answer, email }) {
  const value = toNumber(answer);
  const offset = (email?.length ?? 0) % 3;
  const expected = project2Fixtures.rateMinutes + offset;
  const correct = Number.isFinite(value) && value === expected;
  return {
    correct,
    reason: correct ? "" : "Compute minutes given limits, then add (email length mod 3) as described",
  };
}

function checkDemo3Guard({ answer }) {
  const text = `${answer}`.toLowerCase();
  const hasJson = text.includes("json");
  const hasPii = text.includes("pii") || text.includes("personal");
  const hasUnknown = text.includes("unknown");
  const hasRefusal = text.includes("refuse") || text.includes("reject") || text.includes("decline");
  const correct = hasJson && hasPii && hasUnknown && hasRefusal;
  return { correct, reason: correct ? "" : "Prompt should enforce JSON-only, refuse PII, and allow unknown fallback" };
}

function checkDemo3Rag({ answer }) {
  const ids = parseIdList(answer);
  const expected = project2Fixtures.ragTop.join(",");
  const correct = ids.join(",") === expected;
  return { correct, reason: correct ? "" : "Rank by 0.6*lex + 0.4*vector" };
}

function checkDemo3F1({ answer }) {
  const parsed = parseJsonAnswer(answer);
  const runId = `${parsed?.run_id ?? parsed?.runId ?? ""}`.trim();
  const macro = toNumber(parsed?.macro_f1 ?? parsed?.macroF1 ?? parsed?.f1);
  if (!runId || !Number.isFinite(macro)) return { correct: false, reason: "Provide run_id and macro_f1" };
  const expected = project2Fixtures.f1;
  const correct = runId === expected.run_id && Math.abs(macro - expected.macro_f1) < 0.0005;
  return { correct, reason: correct ? "" : "Return best run id with macro-F1 rounded to 4 decimals" };
}

function parseJsonAnswer(answer) {
  if (typeof answer === "string") {
    try {
      return JSON.parse(answer);
    } catch {
      return null;
    }
  }
  return answer;
}

function normalizePassphrase(answer) {
  const map = { zero: "0", one: "1", two: "2", three: "3", four: "4", five: "5", six: "6", seven: "7", eight: "8", nine: "9" };
  const words = `${answer}`.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/).map((w) => map[w] ?? w);
  return words.join(" ");
}

function normalizeHex(text) {
  const trimmed = `${text}`.trim().replace(/^#/, "").toLowerCase();
  return /^[0-9a-f]{6}$/.test(trimmed) ? `#${trimmed}` : `${text}`.trim().toLowerCase();
}

function parseIdList(answer) {
  if (Array.isArray(answer)) return answer.map((id) => `${id}`.trim().toLowerCase());
  if (typeof answer === "string") return answer.split(/[,\s]+/).map((id) => id.trim().toLowerCase()).filter(Boolean);
  return [];
}

function normalizeArgs(step) {
  if (!step) return {};
  if (typeof step.args === "object") return step.args;
  if (typeof step.arguments === "object") return step.arguments;
  if (typeof step.params === "object") return step.params;
  return {};
}

function escapeRegex(text) {
  return `${text}`.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const toNumber = (value) => {
  const match = `${value}`.match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : NaN;
};

// Fetch local assets (e.g. data files) to validate answers
const assetCache = {};
const getAsset = async (path, env, request) => {
  if (!(path in assetCache)) {
    const url = new URL(path, request.url);
    const text = await env.ASSETS.fetch(url).then(r => r.text());
    assetCache[path] = text;
  }
  return assetCache[path];
};

const sha256 = async (input) => {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
};

const demo2Checksum = async (key) => (await sha256(key + demo2Blob)).slice(0, 12);
