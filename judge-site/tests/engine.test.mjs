import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {webcrypto} from "node:crypto";
if (!globalThis.crypto) globalThis.crypto=webcrypto;
const {verifySource,verifyRecorded,computeReview,makeIntent,exportReview,digest,canonical,CASES}=await import("../dist/engine.js");
const {sourceText,recordedText}=await import("../dist/data.js");
const {PINS}=await import("../dist/integrity.js");
const refs=JSON.parse(await readFile(new URL("./python-reference.json",import.meta.url),"utf8"));
let checks=0;
async function test(name,fn){await fn();checks++;console.log("PASS "+name);}
const source=await verifySource(sourceText);
await test("all three results match the current Python reviewer",async()=>{
  for (const scenario of Object.keys(CASES)) {
    const actual=await computeReview(source,scenario),expected=refs[scenario];
    for (const key of ["candidate_pairs","candidate_s","registered_pairs","baseline_pairs","baseline_s","registered_s","claimed_s","local_result","total_only_match","per_pair_match","reasons","snapshot_sha256","policy_sha256","original_claim_sha256"]) assert.deepEqual(actual[key],expected[key],scenario+" / "+key);
    assert.equal(actual.original_python_reference_receipt_sha256,expected.receipt_sha256);
    assert.equal(actual.provider_calls,0);assert.equal(actual.candidate_execution,"NOT_RUN");
  }
});
await test("wrong total repair fails each pair while preserving the headline total",async()=>{
  const r=await computeReview(source,"same-total");assert.equal(r.candidate_s,2.6);assert.deepEqual(r.candidate_pairs,[.8,.75,.65,-.4]);assert.ok(r.candidate_pairs.every((n,i)=>n!==r.registered_pairs[i]));assert.equal(r.local_result,"REJECTED");
});
await test("missing evidence retains three known values without inventing the fourth or a total",async()=>{
  const r=await computeReview(source,"missing-pair");
  assert.equal(r.candidate_pairs,null);assert.equal(r.candidate_s,null);assert.equal(r.local_result,"REVIEW");
  assert.deepEqual(r.partial_candidate_pairs,[.70,.65,.75,null]);
  assert.equal(r.total_only_match,false);assert.equal(r.per_pair_match,false);
  assert.equal(r.original_claim_unchanged,true);assert.equal(r.claimed_s,3.4);
  const {receipt_sha256,...content}=r;assert.equal(receipt_sha256,await digest(canonical(content)));
  const substituted={...content,partial_candidate_pairs:[.70,.65,.75,r.registered_pairs[3]]};
  assert.notEqual(await digest(canonical(substituted)),receipt_sha256,"Backfilling the absent row must invalidate its receipt");
  assert.throws(()=>exportReview({...r,partial_candidate_pairs:substituted.partial_candidate_pairs}),/SOURCE_NOT_VERIFIED/);
});
await test("tampered raw source is rejected",async()=>{await assert.rejects(verifySource(sourceText.replace('850','851')),/SOURCE_PAYLOAD_CHANGED/);});
await test("same values but altered source serialization cannot reuse raw-byte pin",async()=>{await assert.rejects(verifySource(JSON.stringify(JSON.parse(sourceText),null,2)),/SOURCE_PAYLOAD_CHANGED/);});
await test("unverified copied source cannot enter the calculator",async()=>{await assert.rejects(computeReview(JSON.parse(sourceText),"channel-fix"),/SOURCE_NOT_VERIFIED/);assert.throws(()=>{source.counts.rows[0][0]=0;},TypeError);});
await test("receipt binds source, candidate and actual computed result",async()=>{
  const r=await computeReview(source,"channel-fix");const {receipt_sha256,...content}=r;
  assert.equal(receipt_sha256,await digest(canonical(content)));assert.equal(r.source_payload_sha256,PINS.source_sha256);assert.equal(r.candidate_source_sha256,await digest(r.candidate_source));assert.equal(r.snapshot_sha256,refs["channel-fix"].snapshot_sha256);
  assert.equal(r.receipt_sha256,"82987c0d0bb0e5f416a96910991cde872d7d47e5f201712071516bb8214aeccf","Complete case A must retain its published receipt");
  assert.equal((await computeReview(source,"same-total")).receipt_sha256,"c10b563970962938abd71e1abf776cbcbf48015aebdc9650337d4262eff7785f","Complete case B must retain its published receipt");
});
await test("stale receipt and cross-scenario intent are refused",async()=>{
  const a=await computeReview(source,"channel-fix"),b=await computeReview(source,"same-total");
  assert.throws(()=>makeIntent(a,"hold-for-evidence",b.receipt_sha256),/STALE_REVIEW_RECEIPT/);
  const intent=makeIntent(a,"hold-for-evidence",a.receipt_sha256);assert.throws(()=>exportReview(b,intent),/INTENT_BINDING_INVALID/);
  assert.throws(()=>exportReview(a,{...intent,authorizes_payment:true}),/INTENT_BINDING_INVALID/);
  for (const key of ["executes_candidate","authorizes_payment","changes_scientific_claim","persisted_by_service"]) assert.equal(intent[key],false);
  assert.throws(()=>makeIntent(a,"approve-claim",a.receipt_sha256),/INVALID_REVIEW_CHOICE/);
});
await test("modified review objects and unknown cases do not pass as trusted review",async()=>{
  const r=await computeReview(source,"channel-fix");assert.throws(()=>exportReview({...r}),/SOURCE_NOT_VERIFIED/);await assert.rejects(computeReview(source,"__proto__"),/UNKNOWN_SCENARIO/);
});
await test("saved cloud evidence is independently pinned and tampering is rejected",async()=>{
  const recorded=await verifyRecorded(recordedText);assert.equal(recorded.generation.http_status,200);assert.equal(recorded.generation.prompt_tokens,121);assert.equal(recorded.generation.completion_tokens,38);assert.equal(recorded.sandbox.operation_count,1);assert.equal(recorded.sandbox.duration_seconds,1.273);
  assert.deepEqual(recorded.cases.map(c=>c.checks_passed),[2,4,3]);await assert.rejects(verifyRecorded(recordedText.replace('1.273','0.000')),/RECORDED_EVIDENCE_CHANGED/);
});
await test("standalone HTML needs no module imports, fetch or external assets",async()=>{
  const html=await readFile(new URL("../dist/index.html",import.meta.url),"utf8");
  assert.ok(!/<script[^>]+src=|<link[^>]+href=|type="module"|\bfetch\s*\(/i.test(html));
  assert.ok(!/^import\s/m.test(html));assert.ok(html.includes("connect-src 'none'"));
  assert.ok(!/\b(?:eval|Function)\s*\(|https?:\/\//.test(html));
});
await test("standalone CSP hashes cover the exact inline code and style bytes",async()=>{
  const html=await readFile(new URL("../dist/index.html",import.meta.url),"utf8");
  const {createHash}=await import("node:crypto");
  for (const tag of ["script","style"]) {const content=html.match(new RegExp("<"+tag+">([\\s\\S]*?)</"+tag+">"))[1];assert.ok(html.includes("'sha256-"+createHash("sha256").update(content).digest("base64")+"'"));}
});
console.log(JSON.stringify({checks,status:"PASS",provider_calls:0,scope:"Offline browser-engine parity, negative controls, source/intent binding and portable build integrity."}));
