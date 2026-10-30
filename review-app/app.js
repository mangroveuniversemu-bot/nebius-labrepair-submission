"use strict";
const byId = id => document.getElementById(id);
const format = value => value == null ? "—" : Number(value).toFixed(2);
let currentReview = null;
let currentDecision = null;
let reviewBusy = false;
let decisionSequence = 0;
let decisionBusy = false;
const samples = [...document.querySelectorAll(".sample")];

async function requestJSON(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(path, {...options, signal: controller.signal, cache: "no-store"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "REVIEW_UNAVAILABLE");
    return result;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("REQUEST_TIMED_OUT · no automatic retry");
    throw error;
  } finally { clearTimeout(timer); }
}
const action = (path, body) => requestJSON(path, {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
});
function setState(id, state, label = state) {
  byId(id).dataset.state = state; byId(id).textContent = label;
}
function updateDownload() {
  byId("download").setAttribute("aria-disabled", String(!currentReview));
  if (!currentReview) { byId("download").href = "#"; return; }
  const query = new URLSearchParams({scenario: currentReview.scenario,
    receipt_sha256: currentReview.receipt_sha256, choice: currentDecision ? currentDecision.choice : "none"});
  byId("download").href = "/download?" + query;
  byId("download").download = "labrepair-" + currentReview.scenario + ".json";
}
function textCell(row, value, cls) {
  const cell = document.createElement("td"); cell.textContent = value;
  if (cls) cell.className = cls; row.append(cell);
}
function clearReview() {
  decisionSequence += 1; decisionBusy = false;
  currentReview = null; currentDecision = null;
  ["hold", "rerun"].forEach(id => byId(id).disabled = true);
  updateDownload();
  byId("candidate").textContent = "—";
  byId("candidate-detail").textContent = "Run a check to inspect this candidate.";
  byId("verdict").textContent = "Awaiting review";
  delete byId("verdict").parentElement.dataset.kind;
  byId("verdict-detail").textContent = "Run the selected sample to inspect its evidence.";
  byId("pairs").replaceChildren();
  const row = document.createElement("tr"), cell = document.createElement("td");
  cell.colSpan = 4; cell.textContent = "Run a review to compare the evidence."; row.append(cell); byId("pairs").append(row);
  byId("diff").textContent = "No proposal reviewed yet.";
  byId("snapshot").textContent = "—";
  byId("trap").textContent = "A matching S value can hide the wrong pair correlations. Compare sample A with sample B.";
  byId("steps").replaceChildren();
  byId("decision-note").textContent = "Review intent only. Nothing is dispatched.";
  setState("review-state", "READY");
  samples.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.scenario === byId("scenario").value)));
}
function render(result) {
  currentReview = result; currentDecision = null;
  byId("claimed").textContent = format(result.claimed_s);
  byId("baseline").textContent = format(result.baseline_s);
  byId("registered").textContent = format(result.registered_s);
  byId("candidate").textContent = Number.isFinite(result.candidate_s) ? format(result.candidate_s) : "—";
  const pairValues = result.candidate_pairs || [];
  const knownPairs = result.pairs.filter((_, index) => Number.isFinite(pairValues[index])).length;
  const matchingPairs = result.pairs.filter((_, index) => Number.isFinite(pairValues[index]) && Math.abs(pairValues[index] - result.registered_pairs[index]) < 1e-12).length;
  byId("candidate-detail").textContent = knownPairs < result.pairs.length
    ? knownPairs + " of " + result.pairs.length + " pair values available · missing stays unknown"
    : matchingPairs + " of " + result.pairs.length + " pair values match";
  const labels = {LOCAL_SEMANTIC_MATCH: "Locally consistent", REJECTED: "Proposal rejected", REVIEW: "More evidence needed"};
  const states = {LOCAL_SEMANTIC_MATCH: "PASS", REJECTED: "FAIL", REVIEW: "REVIEW"};
  setState("review-state", states[result.local_result] || "FAIL");
  byId("verdict").textContent = labels[result.local_result] || "Review blocked";
  byId("verdict").parentElement.dataset.kind = result.local_result;
  byId("verdict-detail").textContent = result.local_result === "LOCAL_SEMANTIC_MATCH"
    ? "All pair values match. No new isolated run is authorized by this review."
    : result.reasons.join(" · ").replaceAll("_", " ").toLowerCase();
  byId("pairs").replaceChildren();
  result.pairs.forEach((pair, index) => {
    const row = document.createElement("tr"), value = result.candidate_pairs && result.candidate_pairs[index];
    const matches = value != null && Math.abs(value - result.registered_pairs[index]) < 1e-12;
    textCell(row, pair); textCell(row, format(result.registered_pairs[index])); textCell(row, format(value));
    textCell(row, value == null ? "UNKNOWN" : matches ? "MATCH" : "DIFF", value == null ? "unknown" : matches ? "ok" : "bad");
    byId("pairs").append(row);
  });
  byId("trap").textContent = result.total_only_match && !result.per_pair_match
    ? "The candidate total matches 2.60, but its pair values disagree. A total-only check would accept this wrong repair; the full evidence check rejects it."
    : result.per_pair_match ? "All four registered pair values match. The original 3.40 scientific claim still remains not reproduced."
    : "No complete pairwise match has been established. A plausible explanation cannot replace missing or conflicting evidence.";
  byId("diff").replaceChildren();
  const diff = result.changes.map(change => change.diff).join("\n") || "No admissible source diff. The proposal was refused before review.";
  diff.split("\n").forEach(line => {
    const span = document.createElement("span"); span.textContent = line || " ";
    if (line.startsWith("+") && !line.startsWith("+++")) span.className = "added";
    if (line.startsWith("-") && !line.startsWith("---")) span.className = "removed";
    byId("diff").append(span);
  });
  byId("snapshot").textContent = result.snapshot_sha256;
  byId("steps").replaceChildren();
  result.steps.forEach(step => {
    const li = document.createElement("li"), b = document.createElement("b"); b.textContent = step.tool;
    li.append(b, document.createTextNode(step.result)); byId("steps").append(li);
  });
  ["hold", "rerun"].forEach(id => byId(id).disabled = false);
  updateDownload();
  byId("decision-note").textContent = "Review intent only. Nothing is dispatched.";
  byId("run-status").textContent = "Local review complete · no cloud call";
}
byId("run").addEventListener("click", async () => {
  if (reviewBusy) return;
  clearReview(); reviewBusy = true;
  byId("run").disabled = true; byId("scenario").disabled = true; samples.forEach(b => b.disabled = true);
  byId("review-results").setAttribute("aria-busy", "true"); setState("review-state", "RUNNING");
  byId("run-status").textContent = "Inspecting source and recomputing evidence…";
  try { render(await action("/api/review", {scenario: byId("scenario").value})); }
  catch (error) { clearReview(); setState("review-state", "FAIL", "REVIEW UNAVAILABLE"); byId("run-status").textContent = "Review blocked: " + error.message; }
  finally {
    reviewBusy = false; byId("run").disabled = false; byId("scenario").disabled = false;
    samples.forEach(b => b.disabled = false); byId("review-results").setAttribute("aria-busy", "false");
  }
});
byId("scenario").addEventListener("change", () => {
  clearReview(); byId("run-status").textContent = "Sample selected · run a fresh local review";
});
samples.forEach(button => button.addEventListener("click", () => {
  if (reviewBusy || byId("scenario").disabled) return;
  byId("scenario").value = button.dataset.scenario; clearReview();
  byId("run-status").textContent = "Sample selected · no inference or review started";
}));
async function decision(choice) {
  if (!currentReview || decisionBusy) return;
  const reviewed = currentReview, sequence = ++decisionSequence;
  decisionBusy = true;
  ["hold", "rerun"].forEach(id => byId(id).disabled = true);
  byId("decision-note").textContent = "Recording intent for this reviewed source…";
  try {
    const result = await action("/api/decision", {scenario: reviewed.scenario, receipt_sha256: reviewed.receipt_sha256, choice});
    if (sequence !== decisionSequence || currentReview !== reviewed) return;
    currentDecision = result;
    updateDownload(); byId("decision-note").textContent = choice === "hold-for-evidence"
      ? "Recorded: hold for evidence. Original claim unchanged; no execution authorized."
      : "Recorded: request an isolated rerun after cost and runtime checks. Nothing was dispatched.";
  } catch (error) {
    if (sequence === decisionSequence && currentReview === reviewed) byId("decision-note").textContent = "Decision not recorded: " + error.message;
  } finally {
    if (sequence === decisionSequence && currentReview === reviewed) {
      decisionBusy = false; ["hold", "rerun"].forEach(id => byId(id).disabled = false);
    }
  }
}
byId("hold").addEventListener("click", () => decision("hold-for-evidence"));
byId("rerun").addEventListener("click", () => decision("request-isolated-rerun"));
["download", "download-recorded"].forEach(id => byId(id).addEventListener("click", event => {
  if (byId(id).getAttribute("aria-disabled") === "true") event.preventDefault();
}));
async function initialize() {
  try {
    const {scenarios, capabilities: c} = await requestJSON("/api/status");
    Object.entries(scenarios).forEach(([value, label]) => {
      const option = document.createElement("option"); option.value = value; option.textContent = label; byId("scenario").append(option);
    });
    const statuses = [["Separate NVIDIA developer endpoint", c.nvidia_developer_smoke.status],
      ["Earlier Nebius model catalog observation", c.nebius_model_catalog.status],
      ["Earlier Sandbox permissions observation", c.nebius_sandbox_permissions.status],
      ["Recorded Nebius generation", c.nebius_generation], ["Recorded Sandbox execution", c.nebius_sandbox_execution],
      ["Account spending guard", c.monetary_guard]];
    statuses.forEach(([label, value]) => {
      const div = document.createElement("div"), strong = document.createElement("strong"); strong.textContent = value;
      div.append(document.createTextNode(label), strong); byId("capability-list").append(div);
    });
    byId("scenario").disabled = false; byId("run").disabled = false;
    byId("run-status").textContent = "READY · choose a sample, then run its review";
  } catch (error) {
    samples.forEach(b => b.disabled = true); setState("review-state", "FAIL", "SETUP UNAVAILABLE");
    byId("run-status").textContent = "Setup unavailable: " + error.message;
  }
}
async function loadRecordedValidation() {
  try {
    const r = await requestJSON("/api/recorded-validation");
    byId("recorded-description").textContent = r.description;
    byId("recorded-tokens").textContent = r.generation.prompt_tokens + " in · " + r.generation.completion_tokens + " out";
    byId("recorded-runtime").textContent = r.sandbox.operation_count + " operation · " + Number(r.sandbox.duration_seconds).toFixed(3) + " s";
    byId("recorded-cases").replaceChildren();
    r.cases.forEach(c => {
      const row = document.createElement("tr"); textCell(row, c.label); textCell(row, format(c.total_s));
      textCell(row, c.checks_passed + "/" + c.tests_run); textCell(row, c.outcome, c.case === "model_fix" ? "ok" : "control");
      byId("recorded-cases").append(row);
    });
    byId("recorded-boundary").textContent = r.boundary;
    byId("recorded-model").textContent = "Nebius Token Factory · " + r.generation.model + " · observed " + r.observed_utc;
    byId("recorded-provenance").textContent = r.provenance;
    byId("recorded-operation").textContent = "Operation " + r.sandbox.operation_id;
    byId("recorded-content").hidden = false;
    byId("download-recorded").href = "/download-recorded"; byId("download-recorded").setAttribute("aria-disabled", "false");
    setState("recorded-state", "PASS", "VERIFIED RECORDED RUN · NO NEW CALL");
  } catch (error) {
    byId("recorded-content").hidden = true;
    byId("recorded-description").textContent = "Saved evidence could not be verified. No successful cloud run is shown by this readback. Local samples remain separate.";
    byId("recorded-error").hidden = false;
    byId("recorded-error").textContent = "Evidence unavailable: " + error.message + ". Restore the original pinned files and reload; no automatic retry or provider call.";
    setState("recorded-state", "FAIL", "SAVED EVIDENCE UNAVAILABLE");
  }
}
initialize();
loadRecordedValidation();
