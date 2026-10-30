"use strict";

// Exercise the shipped browser code and its installed listeners without a
// browser dependency, network request, provider call, or candidate execution.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "review-app", "app.js"), "utf8");

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}

function response(body) {
  return {ok: true, json: async () => body};
}

class Element {
  constructor() {
    this.dataset = {};
    this.attributes = new Map();
    this.listeners = new Map();
    this.children = [];
    this.parentElement = {dataset: {}};
    this.disabled = false;
    this.textContent = "";
    this.value = "";
  }
  addEventListener(name, listener) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(listener);
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  // Deliberately invoke the real listener even while disabled, as a queued
  // event could arrive after the first click. The JS guard must also refuse it.
  fire(name) {
    const listeners = this.listeners.get(name) || [];
    assert.equal(listeners.length, 1, `Expected one installed ${name} listener`);
    return listeners[0]({preventDefault() {}});
  }
}

function review(scenario) {
  return {
    scenario, receipt_sha256: scenario === "channel-fix" ? "a".repeat(64) : "b".repeat(64),
    claimed_s: 3.4, baseline_s: 0.2, registered_s: 2.6,
    local_result: scenario === "channel-fix" ? "LOCAL_SEMANTIC_MATCH" : "REJECTED",
    reasons: scenario === "channel-fix" ? [] : ["PER_PAIR_EVIDENCE_MISMATCH"],
    pairs: ["A0B0", "A0B1", "A1B0", "A1B1"],
    registered_pairs: [0.65, 0.65, 0.65, -0.65],
    candidate_pairs: scenario === "channel-fix" ? [0.65, 0.65, 0.65, -0.65] : [0.75, 0.75, 0.55, -0.55],
    total_only_match: true, per_pair_match: scenario === "channel-fix",
    changes: [{diff: "-CHANNEL_SIGNS = (1, 1, 1, 1)\n+CHANNEL_SIGNS = (1, 1, -1, -1)"}],
    snapshot_sha256: "c".repeat(64), steps: [{tool: "compare_pairwise", result: "Synthetic fixture only"}],
  };
}

async function harness() {
  const elements = new Map();
  const byId = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const samples = ["channel-fix", "same-total"].map(scenario => {
    const button = new Element(); button.dataset.scenario = scenario; return button;
  });
  byId("scenario").value = "channel-fix";
  const pending = [];
  const requests = [];
  const context = vm.createContext({
    document: {
      getElementById: byId, querySelectorAll: () => samples,
      createElement: () => new Element(), createTextNode: text => ({textContent: text}),
    },
    URLSearchParams,
    AbortController: class { constructor() { this.signal = {}; } abort() {} },
    setTimeout: () => 0, clearTimeout: () => {},
    fetch(url, options = {}) {
      requests.push({url, options});
      if (url === "/api/status") return Promise.resolve(response({
        scenarios: {"channel-fix": "Sample A", "same-total": "Sample B"},
        capabilities: {
          nvidia_developer_smoke: {status: "NOT_RUN"}, nebius_model_catalog: {status: "NOT_RUN"},
          nebius_sandbox_permissions: {status: "NOT_RUN"}, nebius_generation: "NOT_RUN",
          nebius_sandbox_execution: "NOT_RUN", monetary_guard: "UNVERIFIED",
        },
      }));
      if (url === "/api/recorded-validation") return Promise.reject(new Error("RECORDED_EVIDENCE_UNAVAILABLE"));
      assert.ok(["/api/review", "/api/decision"].includes(url), `Unexpected route: ${url}`);
      const gate = deferred();
      pending.push({url, body: JSON.parse(options.body), gate});
      return gate.promise;
    },
  });
  vm.runInContext(source, context, {filename: "review-app/app.js"});
  // Settle the independent initialization/readback promises before interacting.
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(byId("run").disabled, false);
  assert.equal(byId("recorded-state").dataset.state, "FAIL");
  const countDecisions = () => pending.filter(request => request.url === "/api/decision").length;
  const latest = url => pending.filter(request => request.url === url).at(-1);
  const download = () => new URL(byId("download").href, "http://127.0.0.1").searchParams;
  async function run(scenario) {
    const sample = samples.find(button => button.dataset.scenario === scenario);
    sample.fire("click");
    const completion = byId("run").fire("click");
    const request = latest("/api/review");
    assert.equal(request.body.scenario, scenario);
    request.gate.resolve(response(review(scenario)));
    await completion;
  }
  function finishDecision(request) {
    request.gate.resolve(response({choice: request.body.choice, review_receipt_sha256: request.body.receipt_sha256}));
  }
  return {byId, run, latest, download, finishDecision, countDecisions, requests};
}

test("late Sample A decision cannot contaminate the completed Sample B review", async () => {
  const h = await harness();
  await h.run("channel-fix");
  const aDone = h.byId("hold").fire("click"), aRequest = h.latest("/api/decision");
  assert.equal(aRequest.body.scenario, "channel-fix");
  assert.equal(h.byId("hold").disabled, true);
  assert.equal(h.byId("rerun").disabled, true);
  await h.run("same-total");
  const bNote = h.byId("decision-note").textContent;
  assert.equal(h.download().get("scenario"), "same-total");
  assert.equal(h.download().get("choice"), "none");
  h.finishDecision(aRequest); await aDone;
  assert.equal(h.download().get("scenario"), "same-total");
  assert.equal(h.download().get("receipt_sha256"), "b".repeat(64));
  assert.equal(h.download().get("choice"), "none");
  assert.equal(h.byId("decision-note").textContent, bNote);
  assert.doesNotMatch(h.byId("decision-note").textContent, /Recorded:/);
  assert.equal(h.byId("hold").disabled, false);
  assert.equal(h.byId("rerun").disabled, false);
});

test("pending intent disables both controls and refuses overlapping Hold or Rerun", async () => {
  const h = await harness(); await h.run("channel-fix");
  const firstDone = h.byId("hold").fire("click"), first = h.latest("/api/decision");
  assert.equal(h.byId("hold").disabled, true);
  assert.equal(h.byId("rerun").disabled, true);
  await h.byId("hold").fire("click");
  await h.byId("rerun").fire("click");
  assert.equal(h.countDecisions(), 1);
  assert.equal(h.download().get("choice"), "none");
  h.finishDecision(first); await firstDone;
  assert.equal(h.byId("hold").disabled, false);
  assert.equal(h.byId("rerun").disabled, false);
  assert.equal(h.download().get("choice"), "hold-for-evidence");
  const nextDone = h.byId("rerun").fire("click"), next = h.latest("/api/decision");
  assert.equal(h.countDecisions(), 2);
  h.finishDecision(next); await nextDone;
  assert.equal(h.download().get("choice"), "request-isolated-rerun");
});

test("stale A completion does not unlock controls for B's newer pending intent", async () => {
  const h = await harness(); await h.run("channel-fix");
  const aDone = h.byId("hold").fire("click"), a = h.latest("/api/decision");
  await h.run("same-total");
  const bDone = h.byId("rerun").fire("click"), b = h.latest("/api/decision");
  const pendingBNote = h.byId("decision-note").textContent;
  h.finishDecision(a); await aDone;
  assert.equal(h.byId("hold").disabled, true);
  assert.equal(h.byId("rerun").disabled, true);
  assert.equal(h.byId("decision-note").textContent, pendingBNote);
  assert.equal(h.download().get("choice"), "none");
  await h.byId("hold").fire("click");
  assert.equal(h.countDecisions(), 2);
  h.finishDecision(b); await bDone;
  assert.equal(h.download().get("scenario"), "same-total");
  assert.equal(h.download().get("choice"), "request-isolated-rerun");
  assert.equal(h.byId("hold").disabled, false);
  assert.equal(h.byId("rerun").disabled, false);
});
