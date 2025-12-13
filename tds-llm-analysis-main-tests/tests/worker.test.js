// @ts-check
import { afterEach, describe, expect, vi } from "vitest";
import { demo2Blob, demo2Key, emailNumber } from "../public/utils.js";
import worker from "../src/worker.js";
import { makeStory, resetStage } from "./support.js";

const story = makeStory(worker);
const sha256 = async (input) => {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
};

describe("worker", () => {
  afterEach(() => {
    resetStage();
  });

  story("static routes are served from ASSETS", async (scene) => {
    scene.assets.serve("bundled file");
    const response = await scene.get("/guide");

    expect(scene.assets.requests()).toEqual(["/guide"]);
    expect(await scene.text(response)).toBe("bundled file");
  });

  story("submit insists on POST", async (scene) => {
    const response = await scene.get("/submit");
    const body = await scene.json(response);

    expect(response.status).toBe(405);
    expect(body.error).toBe("Use POST /submit");
  });

  story("submit demands valid JSON", async (scene) => {
    const response = await scene.post("/submit", { body: "not json", raw: true });
    const body = await scene.json(response);

    expect(response.status).toBe(400);
    expect(body.error).toMatch("Body must be valid JSON");
  });

  story("submit requires every field", async (scene) => {
    const response = await scene.submit((form) => delete form.secret);
    const body = await scene.json(response);

    expect(response.status).toBe(400);
    expect(body.error).toBe("Missing field secret");
  });

  story("submit validates parent ids", async (scene) => {
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo", { id: 999 });
    });
    const body = await scene.json(response);

    expect(response.status).toBe(400);
    expect(body.error).toBe("Invalid id=999");
  });

  story("submit rejects unknown endpoints", async (scene) => {
    const response = await scene.submit((form) => {
      form.url = scene.link("/mystery");
    });
    const body = await scene.json(response);

    expect(response.status).toBe(400);
    expect(body.error).toMatch("Unknown url");
  });

  story("demo step records attempts and points to scrape task", async (scene) => {
    const response = await scene.submit();
    const body = await scene.json(response);
    const inserted = scene.db.inserted();
    const updated = scene.db.updated();

    expect(response.status).toBe(200);
    expect(body).toMatchObject({
      correct: true,
      reason: "",
      url: scene.link("/demo-scrape", { email: "alice@example.com", id: inserted.id }),
      delay: null,
    });
    expect(inserted).toMatchObject({
      email: "alice@example.com",
      ip: "203.0.113.10",
      url: scene.link("/demo"),
    });
    expect(updated).toMatchObject({
      id: inserted.id,
      correct: true,
      reason: "",
      next_url: body.url,
    });
  });

  story("demo-scrape checks shared secret", async (scene) => {
    scene.withParent({
      id: 1,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      secret: "parent",
      url: scene.link("/demo"),
      answer: "x",
    });
    scene.at("2024-04-08T00:00:10.000Z");
    const secret = await emailNumber("alice@example.com");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo-scrape", { email: form.email, id: 1 });
      form.answer = String(secret);
    });
    const body = await scene.json(response);
    const inserted = scene.db.inserted();

    expect(body).toMatchObject({
      correct: true,
      reason: "",
      url: scene.link("/demo-audio", { email: "alice@example.com", id: inserted.id }),
    });
    expect(scene.db.updated()).toMatchObject({
      correct: true,
      next_url: body.url,
    });
  });

  story("demo-scrape reports mismatched secret", async (scene) => {
    scene.withParent({
      id: 1,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
    });
    scene.at("2024-04-08T00:00:10.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo-scrape", { email: form.email, id: 1 });
      form.answer = "wrong";
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: false,
      reason: "Secret mismatch",
    });
  });

  story("demo-audio sums the qualifying samples", async (scene) => {
    const parent = scene.withParent({
      id: 7,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
    });
    scene.at("2024-04-08T00:00:20.000Z");
    const cutoff = await emailNumber("alice@example.com");
    const samples = [cutoff - 1, cutoff, cutoff + 1];
    const expected = samples.filter((n) => n >= cutoff).reduce((sum, n) => sum + n, 0);
    scene.assets.file("/demo-audio-data.csv", samples.join("\n"));

    const response = await scene.submit((form) => {
      form.url = scene.link("/demo-audio", { id: parent.id, email: form.email });
      form.answer = String(expected);
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: true,
      reason: "",
      url: null,
    });
    expect(scene.assets.requests()).toContain("/demo-audio-data.csv");
  });

  story("demo-audio flags a wrong sum", async (scene) => {
    scene.withParent({
      id: 2,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
    });
    scene.at("2024-04-08T00:00:20.000Z");
    const cutoff = await emailNumber("alice@example.com");
    const samples = [cutoff, cutoff + 1, cutoff + 2];
    const expected = samples.filter((n) => n >= cutoff).reduce((sum, n) => sum + n, 0);
    scene.assets.file("/demo-audio-data.csv", samples.join("\n"));
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo-audio", { id: 2, email: form.email });
      form.answer = String(expected + 1);
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: false,
      reason: "Wrong sum of numbers",
    });
  });

  story("demo2 validates the alphametic key and points to checksum", async (scene) => {
    const key = await demo2Key("alice@example.com");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo2");
      form.answer = key;
    });
    const body = await scene.json(response);
    const inserted = scene.db.inserted();

    expect(body).toMatchObject({
      correct: true,
      reason: "",
      url: scene.link("/demo2-checksum", { email: "alice@example.com", id: inserted.id }),
    });
  });

  story("demo2 rejects a wrong key", async (scene) => {
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo2");
      form.answer = "00000000";
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: false,
      reason: "Key mismatch",
    });
  });

  story("demo2-checksum accepts the correct digest", async (scene) => {
    const key = await demo2Key("alice@example.com");
    const expected = (await sha256(key + demo2Blob)).slice(0, 12);
    scene.withParent({
      id: 5,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/demo2"),
    });
    scene.at("2024-04-08T00:00:20.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo2-checksum", { id: 5, email: form.email });
      form.answer = expected;
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: true,
      reason: "",
      url: null,
    });
  });

  story("demo2-checksum flags a wrong digest", async (scene) => {
    scene.withParent({
      id: 6,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/demo2"),
    });
    scene.at("2024-04-08T00:00:20.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo2-checksum", { id: 6, email: form.email });
      form.answer = "deadbeefcafe";
    });
    const body = await scene.json(response);

    expect(body).toMatchObject({
      correct: false,
      reason: "Checksum mismatch",
    });
  });

  story("project2 start advances to the UV task", async (scene) => {
    const response = await scene.submit((form) => {
      form.url = scene.link("/project2");
      form.answer = "ready";
    });
    const body = await scene.json(response);
    const inserted = scene.db.inserted();

    expect(body.correct).toBe(true);
    expect(body.url).toBe(scene.link("/project2-uv", { email: "alice@example.com", id: inserted.id }));
  });

  story("project2 difficulty 2 reveals next url even on wrong answer", async (scene) => {
    const parent = scene.withParent({
      id: 11,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/project2-md"),
    });
    scene.at("2024-04-08T00:00:05.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/project2-audio-passphrase", { email: form.email, id: parent.id });
      form.answer = "not the passphrase";
    });
    const body = await scene.json(response);
    const inserted = scene.db.inserted();

    expect(body.correct).toBe(false);
    expect(body.url).toBe(scene.link("/project2-heatmap", { email: "alice@example.com", id: inserted.id }));
  });

  story("project2 difficulty 3 blocks progress on wrong answer", async (scene) => {
    const parent = scene.withParent({
      id: 12,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/project2-csv"),
    });
    scene.at("2024-04-08T00:00:05.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/project2-gh-tree", { email: form.email, id: parent.id });
      form.answer = "0";
    });
    const body = await scene.json(response);

    expect(body.correct).toBe(false);
    expect(body.url).toBeNull();
  });

  story("project2 difficulty 3 reveals next url when correct", async (scene) => {
    const parent = scene.withParent({
      id: 13,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/project2-csv"),
    });
    scene.at("2024-04-08T00:00:05.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/project2-gh-tree", { email: form.email, id: parent.id });
      form.answer = "2"; // base 1 + (email length mod 2) => 1 + 1
    });
    const body = await scene.json(response);
    const inserted = scene.db.inserted();

    expect(body.correct).toBe(true);
    expect(body.url).toBe(scene.link("/project2-logs", { email: "alice@example.com", id: inserted.id }));
  });

  story("project2 embed personalizes expected pair by email length", async (scene) => {
    const parent = scene.withParent({
      id: 15,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "even@example.com", // even length => expect s4,s5
      url: scene.link("/project2-shards"),
    });
    scene.at("2024-04-08T00:00:05.000Z");
    const response = await scene.submit((form) => {
      form.email = "even@example.com";
      form.url = scene.link("/project2-embed", { email: form.email, id: parent.id });
      form.answer = "s4,s5";
    });
    const body = await scene.json(response);

    expect(body.correct).toBe(true);
    expect(body.url).toBe(scene.link("/project2-tools", { email: "even@example.com", id: scene.db.inserted().id }));
  });

  story("project2 final step validates macro-F1", async (scene) => {
    const parent = scene.withParent({
      id: 14,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
      url: scene.link("/project2-rag"),
    });
    scene.at("2024-04-08T00:00:05.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/project2-f1", { email: form.email, id: parent.id });
      form.answer = JSON.stringify({ run_id: "runC", macro_f1: 0.8175 });
    });
    const body = await scene.json(response);

    expect(body.correct).toBe(true);
    expect(body.url).toBeNull();
  });

  story("submit penalizes slow answers", async (scene) => {
    scene.withParent({
      id: 3,
      timestamp: "2024-04-08T00:00:00.000Z",
      email: "alice@example.com",
    });
    scene.at("2024-04-08T00:05:00.000Z");
    const response = await scene.submit((form) => {
      form.url = scene.link("/demo", { id: 3 });
    });
    const body = await scene.json(response);

    expect(body.correct).toBe(false);
    expect(body.reason).toMatch("[DELAY: 300s > 180s]");
    expect(scene.db.updated()).toMatchObject({
      correct: false,
      reason: body.reason,
      delay: 300,
    });
  });

  story("submit wraps unexpected errors", async (scene) => {
    scene.breakDb();
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await scene.submit();
    const body = await scene.json(response);

    expect(response.status).toBe(500);
    expect(body.error).toMatch("Internal error");
    expect(errorSpy).toHaveBeenCalledWith("Unhandled /submit error", expect.any(Error));
  });
});
