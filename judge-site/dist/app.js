"use strict";
import {sourceText,recordedText} from "./data.js";
import {CASES,verifySource,verifyRecorded,computeReview,makeIntent,exportReview} from "./engine.js";
const byId=id=>document.getElementById(id), samples=[...document.querySelectorAll(".sample")];
const format=n=>n==null?"—":Number(n).toFixed(2);
let source=null,recorded=null,selected="same-total",review=null,intent=null,busy=false,epoch=0;
const links=new Set();
function chip(id,state,label){byId(id).dataset.state=state;byId(id).textContent=label;}
function controls(){byId("run").disabled=!source||busy;byId("check-wrong").disabled=!source||busy;samples.forEach(b=>b.disabled=!source||busy);["hold","rerun","download"].forEach(id=>byId(id).disabled=!review||busy);}
function clear(){epoch++;review=null;intent=null;byId("candidate-total").textContent="—";byId("candidate-detail").textContent="No repair checked yet";byId("verdict").textContent="Awaiting review";delete byId("verdict").parentElement.dataset.state;byId("verdict-detail").textContent="Select a sample and check its evidence.";chip("result-state","READY","READY");byId("pair-table").replaceChildren();const r=document.createElement("tr"),c=document.createElement("td");c.colSpan=4;c.textContent="Run a check to compare the evidence.";r.append(c);byId("pair-table").append(r);byId("trap").textContent="A matching total is necessary. It is not sufficient.";byId("intent-note").textContent="Review intent only. No cloud action.";byId("receipt").textContent="—";byId("after-source").textContent="Check a repair first.";samples.forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.case===selected)));controls();}
function select(id){if(!Object.hasOwn(CASES,id)||busy)return;selected=id;clear();byId("run-note").textContent="Sample selected. Check its evidence when ready.";}
function cell(row,text,cls){const td=document.createElement("td");td.textContent=text;if(cls)td.className=cls;row.append(td);}
function render(r){
  review=r;intent=null;
  const state={LOCAL_SEMANTIC_MATCH:"PASS",REJECTED:"FAIL",REVIEW:"REVIEW"}[r.local_result];
  const labels={PASS:"Repair matches",FAIL:"Repair rejected",REVIEW:"More evidence needed"};
  chip("result-state",state,state);byId("verdict").parentElement.dataset.state=state;
  byId("verdict").textContent=labels[state];
  byId("verdict-detail").textContent=state==="PASS"?"All four pairs agree. Original claim unchanged.":state==="FAIL"?"The total matches. The pair evidence does not.":"The fourth pair is missing. No complete total is computed.";
  byId("candidate-total").textContent=format(r.candidate_s);
  byId("candidate-detail").textContent=state==="PASS"?"4 of 4 pair values match":state==="FAIL"?"0 of 4 pair values match":"3 known pair values · fourth pair unknown";
  const availablePairs=r.candidate_pairs??r.partial_candidate_pairs;
  byId("pair-table").replaceChildren();
  r.pairs.forEach((pair,i)=>{
    const row=document.createElement("tr"),n=availablePairs?.[i],same=n!=null&&n===r.registered_pairs[i];
    cell(row,pair);cell(row,format(r.registered_pairs[i]));cell(row,n==null?"UNKNOWN":format(n));
    cell(row,n==null?"UNKNOWN":same?"MATCH":"DIFF",n==null?"unknown":same?"ok":"bad");
    byId("pair-table").append(row);
  });
  byId("trap").textContent=state==="FAIL"?"Both repairs produce 2.60. This one changes every pair correlation, so the verifier rejects it.":state==="PASS"?"The declared channel repair matches every registered pair. That still cannot establish the original scientific claim.":"The fourth pair is absent. The three available values cannot stand in for missing evidence.";
  byId("after-source").textContent=r.candidate_source;byId("receipt").textContent=r.receipt_sha256;
  byId("run-note").textContent="Check complete · exact browser arithmetic · no cloud call";controls();
}
function revealResult(){
  const reducedMotion=typeof window.matchMedia==="function"&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Focus announces the new verdict; prevent native focus scrolling from
  // competing with the intentional, motion-aware result reveal.
  byId("verdict").focus({preventScroll:true});
  byId("results").scrollIntoView({behavior:reducedMotion?"auto":"smooth",block:"start"});
}
async function run(){
  if(!source||busy)return;
  clear();const token=epoch;let completed=false;busy=true;controls();
  byId("results").setAttribute("aria-busy","true");chip("result-state","REVIEW","CHECKING");
  byId("run-note").textContent="Recomputing the four pair correlations…";
  try{
    const result=await computeReview(source,selected);
    if(token===epoch){render(result);completed=true;}
  }catch(error){
    if(token===epoch){
      clear();chip("result-state","FAIL","CHECK BLOCKED");
      byId("verdict").parentElement.dataset.state="FAIL";
      byId("verdict").textContent="Check unavailable";
      byId("verdict-detail").textContent="No verified result or review receipt was produced.";
      byId("run-note").textContent=error.message;completed=true;
    }
  }finally{
    busy=false;controls();byId("results").setAttribute("aria-busy","false");
    if(completed)revealResult();
  }
}
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+"\n"],{type:"application/json"}));links.add(url);const a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>{URL.revokeObjectURL(url);links.delete(url);},1000);}
samples.forEach(b=>b.addEventListener("click",()=>select(b.dataset.case)));
byId("run").addEventListener("click",run);
byId("check-wrong").addEventListener("click",()=>{select("same-total");void run();});
function decide(choice){if(!review||busy)return;try{intent=makeIntent(review,choice,review.receipt_sha256);byId("intent-note").textContent=choice==="hold-for-evidence"?"Intent recorded in this page: hold for evidence.":"Intent recorded in this page: request a separately authorized rerun. Nothing dispatched.";}catch(error){intent=null;byId("intent-note").textContent="Intent not recorded: "+error.message;}}
byId("hold").addEventListener("click",()=>decide("hold-for-evidence"));byId("rerun").addEventListener("click",()=>decide("request-isolated-rerun"));
byId("download").addEventListener("click",()=>{if(review&&!busy)download(exportReview(review,intent),"labrepair-browser-"+review.scenario+".json");});
byId("download-saved").addEventListener("click",()=>{if(recorded)download(recorded,"labrepair-saved-cloud-evidence.json");});
window.addEventListener("pagehide",()=>{links.forEach(url=>URL.revokeObjectURL(url));links.clear();});
async function setupSource(){try{source=await verifySource(sourceText);byId("before-source").textContent=source.files["analysis.py"];byId("snapshot").textContent=source.snapshot_sha256;chip("source-state","PASS","PINNED SYNTHETIC SOURCE");clear();byId("run-note").textContent="Ready. Check a fixed repair or choose another sample.";}catch(error){source=null;clear();chip("source-state","FAIL","SOURCE UNAVAILABLE");byId("setup-error").hidden=false;byId("setup-error").textContent="Source verification failed: "+error.message+". Review and downloads remain disabled; no retry or cloud call.";byId("run-note").textContent="Check blocked. Restore the original verified build.";}}
async function setupRecorded(){try{recorded=await verifyRecorded(recordedText);chip("saved-state","PASS","SAVED REAL RUN · NO NEW CALL");byId("usage").textContent=recorded.generation.prompt_tokens+" in · "+recorded.generation.completion_tokens+" out";byId("duration").textContent=Number(recorded.sandbox.duration_seconds).toFixed(3)+" seconds";byId("saved-cases").replaceChildren();recorded.cases.forEach(c=>{const row=document.createElement("tr");cell(row,c.label);cell(row,format(c.total_s));cell(row,c.checks_passed+"/"+c.tests_run);cell(row,c.outcome,c.case==="model_fix"?"ok":"");byId("saved-cases").append(row);});byId("model-info").textContent="Observed model: "+recorded.generation.model+" · "+recorded.observed_utc;byId("saved-provenance").textContent=recorded.provenance;byId("saved-content").hidden=false;byId("download-saved").disabled=false;}catch(error){recorded=null;byId("saved-content").hidden=true;byId("download-saved").disabled=true;chip("saved-state","FAIL","SAVED EVIDENCE UNAVAILABLE");byId("saved-error").hidden=false;byId("saved-error").textContent="Saved evidence verification failed: "+error.message+". No successful cloud run is shown. Browser computation remains separate.";}}
setupSource();setupRecorded();
