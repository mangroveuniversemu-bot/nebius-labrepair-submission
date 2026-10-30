"use strict";
import {PINS} from "./integrity.js";

const verifiedSources = new WeakSet();
const reviews = new WeakSet();
const intents = new WeakSet();
const choices = new Set(["hold-for-evidence", "request-isolated-rerun"]);
export const CASES = Object.freeze({
  "channel-fix": {title: "Declared channel repair", signs: [1,1,-1,-1], offsets: ["0","0","0","0"]},
  "same-total": {title: "Same total, wrong pairs", signs: [1,1,-1,-1], offsets: ["0.1","0.1","-0.1","0.1"]},
  "missing-pair": {title: "Incomplete evidence", signs: [1,1,-1,-1], offsets: ["0","0","0","0"]}
});
for (const c of Object.values(CASES)) { Object.freeze(c.signs); Object.freeze(c.offsets); Object.freeze(c); }
const utf8 = new TextEncoder();
export async function digest(text) {
  if (!globalThis.crypto?.subtle) throw new Error("SECURE_CRYPTO_UNAVAILABLE");
  const bytes = await crypto.subtle.digest("SHA-256", utf8.encode(text));
  return [...new Uint8Array(bytes)].map(x => x.toString(16).padStart(2,"0")).join("");
}
export function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort().map(k => JSON.stringify(k)+":"+canonical(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
function freeze(value) {
  if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
export async function verifySource(text) {
  if (await digest(text) !== PINS.source_sha256) throw new Error("SOURCE_PAYLOAD_CHANGED");
  const data = JSON.parse(text);
  if (data.schema !== "LABREPAIR_FIXED_BROWSER_SOURCE_V1") throw new Error("SOURCE_SCHEMA_INVALID");
  const actual = {};
  if (canonical(Object.keys(data.files).sort()) !== canonical(Object.keys(PINS.source_files).sort())) throw new Error("SOURCE_FILES_INVALID");
  for (const [name, expected] of Object.entries(PINS.source_files)) {
    actual[name] = await digest(data.files[name]);
    if (actual[name] !== expected) throw new Error("PROTECTED_SOURCE_CHANGED");
  }
  if (await digest(canonical(actual)) !== PINS.snapshot_sha256 || data.snapshot_sha256 !== PINS.snapshot_sha256) throw new Error("SOURCE_BINDING_INVALID");
  if (await digest(canonical(data.policy)) !== PINS.policy_sha256 || data.policy_sha256 !== PINS.policy_sha256) throw new Error("POLICY_BINDING_INVALID");
  if (canonical(JSON.parse(data.files["counts.json"])) !== canonical(data.counts)) throw new Error("COUNTS_BINDING_INVALID");
  freeze(data); verifiedSources.add(data); return data;
}
export async function verifyRecorded(text) {
  if (await digest(text) !== PINS.recorded_sha256) throw new Error("RECORDED_EVIDENCE_CHANGED");
  const data = JSON.parse(text);
  if (data.status !== "VERIFIED_RECORDED_END_TO_END_RUN" || data.provider_calls_by_replay !== 0 || data.automatic_cloud_dispatch !== "DISABLED") throw new Error("RECORDED_EVIDENCE_INVALID");
  return freeze(data);
}
const abs = x => x < 0n ? -x : x;
function fraction(n, d=1n) {
  if (d === 0n) throw new Error("INVALID_COUNTS");
  if (d < 0n) { n=-n; d=-d; }
  let a=abs(n), b=d; while (b) [a,b]=[b,a%b];
  return {n:n/a,d:d/a};
}
const add = (a,b) => fraction(a.n*b.d+b.n*a.d,a.d*b.d);
const scale = (a,s) => fraction(a.n*BigInt(s),a.d);
const equal = (a,b) => a.n===b.n && a.d===b.d;
const number = a => Number(a.n)/Number(a.d);
function decimal(value) {
  if (!/^-?\d+(\.\d+)?$/.test(value)) throw new Error("OFFSET_INVALID");
  const digits=value.split("."); return fraction(BigInt(digits.join("")),10n**BigInt(digits[1]?.length||0));
}
function pairValues(rows, signs, offsets) {
  if (rows.length!==4) throw new Error("MISSING_PAIR_EVIDENCE");
  return rows.map((row,i)=>{
    if (row.length!==4 || row.some(x=>!Number.isSafeInteger(x)||x<0)) throw new Error("INVALID_COUNTS");
    const r=row.map(BigInt), sum=r.reduce((a,b)=>a+b,0n);
    return add(scale(fraction(r[0]-r[1]-r[2]+r[3],sum),signs[i]),decimal(offsets[i]));
  });
}
const total = (pairs, terms) => pairs.reduce((s,p,i)=>add(s,scale(p,terms[i])),fraction(0n));

export async function computeReview(source, scenario) {
  if (!verifiedSources.has(source)) throw new Error("SOURCE_NOT_VERIFIED");
  if (!Object.hasOwn(CASES,scenario)) throw new Error("UNKNOWN_SCENARIO");
  const c=CASES[scenario], data=source.counts, zero=["0","0","0","0"];
  const registered=pairValues(data.rows,data.registered_channel_signs,zero);
  const baseline=pairValues(data.rows,[1,1,1,1],zero);
  const rows=scenario==="missing-pair" ? data.rows.slice(0,3) : data.rows;
  let candidate=null, result="REVIEW", reasons=["MISSING_PAIR_EVIDENCE"];
  if (rows.length===4) {
    candidate=pairValues(rows,c.signs,c.offsets);
    const matches=candidate.every((p,i)=>equal(p,registered[i]));
    result=matches?"LOCAL_SEMANTIC_MATCH":"REJECTED";
    reasons=matches?[]:["PER_PAIR_EVIDENCE_MISMATCH"];
  }
  const candidateText=source.files["analysis.py"]
    .replace("CHANNEL_SIGNS = (1, 1, 1, 1)","CHANNEL_SIGNS = ("+c.signs.join(", ")+")")
    .replace("OFFSETS = (0, 0, 0, 0)","OFFSETS = ("+c.offsets.join(", ")+")");
  const report={
    schema:"LABREPAIR_BROWSER_REVIEW_V1", mode:"BROWSER_FIXED_CASE_RECOMPUTATION",
    scenario,title:c.title,source_payload_sha256:PINS.source_sha256,
    snapshot_sha256:source.snapshot_sha256,policy_sha256:source.policy_sha256,
    original_source_sha256:{...PINS.source_files},
    original_python_reference_receipt_sha256:source.reference_receipts[scenario],
    candidate_source_sha256:await digest(candidateText),candidate_source:candidateText,
    candidate_parameters:{signs:[...c.signs],offsets:[...c.offsets]},
    pairs:[...data.pairs],registered_pairs:registered.map(number),baseline_pairs:baseline.map(number),
    claimed_s:Number(data.original_claim.claimed_s),baseline_s:number(total(baseline,data.chsh_terms)),
    registered_s:number(total(registered,data.chsh_terms)),
    candidate_pairs:candidate?candidate.map(number):null,
    candidate_s:candidate?number(total(candidate,data.chsh_terms)):null,
    total_only_match:candidate?equal(total(candidate,data.chsh_terms),total(registered,data.chsh_terms)):false,
    per_pair_match:candidate?candidate.every((p,i)=>equal(p,registered[i])):false,
    local_result:result,reasons,original_claim:data.original_claim,original_claim_unchanged:true,
    original_claim_sha256:await digest(canonical(data.original_claim)),
    source_verified:true,arithmetic:"EXACT_RATIONAL_BIGINT",candidate_execution:"NOT_RUN",
    provider_calls:0,automatic_cloud_dispatch:"DISABLED",actual_provider_charge:"unknown",
    physical_interpretation:"NOT_ESTABLISHED_SYNTHETIC_DATA",
    limitations:["Only three fixed, synthetic candidates are supported.","Candidate Python is never executed or interpreted by this page.","Hashes bind content; they do not authenticate a provider or reviewer.","Saved cloud execution is separate from this browser calculation."]
  };
  report.receipt_sha256=await digest(canonical(report)); freeze(report); reviews.add(report); return report;
}
export function makeIntent(review, choice, expectedReceipt) {
  if (!reviews.has(review) || expectedReceipt!==review.receipt_sha256) throw new Error("STALE_REVIEW_RECEIPT");
  if (!choices.has(choice)) throw new Error("INVALID_REVIEW_CHOICE");
  const intent=freeze({schema:"LABREPAIR_BROWSER_REVIEW_INTENT_V1",choice,
    review_receipt_sha256:review.receipt_sha256,source_payload_sha256:review.source_payload_sha256,
    original_claim_sha256:review.original_claim_sha256,review_intent_only:true,
    executes_candidate:false,authorizes_payment:false,changes_scientific_claim:false,
    persisted_by_service:false});
  intents.add(intent); return intent;
}
export function exportReview(review, intent=null) {
  if (!reviews.has(review)) throw new Error("SOURCE_NOT_VERIFIED");
  if (intent && (!intents.has(intent) || intent.review_receipt_sha256!==review.receipt_sha256 || intent.source_payload_sha256!==review.source_payload_sha256)) throw new Error("INTENT_BINDING_INVALID");
  return {schema:"LABREPAIR_BROWSER_EXPORT_V1",review,review_intent:intent};
}
