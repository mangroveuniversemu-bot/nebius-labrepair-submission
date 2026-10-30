// Offline DOM-contract tests: real app handlers and calculator, modeled DOM.
// These assertions observe requested focus/scroll operations, not browser pixels.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import vm from "node:vm";
import * as engine from "../dist/engine.js";
import {sourceText,recordedText} from "../dist/data.js";

const html=await readFile(new URL("../src/index.html",import.meta.url),"utf8");
const app=(await readFile(new URL("../src/app.js",import.meta.url),"utf8")).replace(/^import .*?;\s*$/gm,"");
const pause=()=>new Promise(resolve=>setTimeout(resolve,1));
async function until(predicate){for(let n=0;n<500;n++){if(predicate())return;await pause();}throw new Error("ASYNC_APP_DID_NOT_SETTLE");}
async function setup({reduced=false,compute=engine.computeReview}={}){
  const trace=[],nodes=new Map();
  class Element{
    constructor(id="",attributes=""){this.id=id;this.dataset={};this.attributes=new Map();this.children=[];this.disabled=/\bdisabled\b/.test(attributes);this.hidden=/\bhidden\b/.test(attributes);this.textContent="";this.parentElement={dataset:{}};this.listeners=new Map();for(const m of attributes.matchAll(/([\w-]+)="([^"]*)"/g))this.attributes.set(m[1],m[2]);}
    append(...children){this.children.push(...children);}replaceChildren(...children){this.children=[...children];}
    setAttribute(k,v){this.attributes.set(k,String(v));}getAttribute(k){return this.attributes.get(k)??null;}
    addEventListener(name,handler){this.listeners.set(name,handler);}
    click(){if(!this.disabled)return this.listeners.get("click")?.({preventDefault(){}});}
    focus(options){trace.push({kind:"focus",id:this.id,options,verdict:nodes.get("verdict").textContent,busy:nodes.get("results").getAttribute("aria-busy")});}
    scrollIntoView(options){trace.push({kind:"scroll",id:this.id,options,verdict:nodes.get("verdict").textContent});}
    remove(){}
  }
  for(const m of html.matchAll(/<[\w-]+\b[^>]*\bid="([^"]+)"[^>]*>/g))nodes.set(m[1],new Element(m[1],m[0]));
  const samples=Object.keys(engine.CASES).map(id=>{const e=new Element("",'disabled');e.dataset.case=id;return e;});
  const document={getElementById(id){assert.ok(nodes.has(id),"Missing actual HTML element: "+id);return nodes.get(id);},querySelectorAll(selector){assert.equal(selector,".sample");return samples;},createElement(){return new Element();},body:new Element("body")};
  const window={addEventListener(){},matchMedia(query){assert.equal(query,"(prefers-reduced-motion: reduce)");return {matches:reduced};}};
  const context=vm.createContext({...engine,computeReview:compute,sourceText,recordedText,document,window,console,setTimeout,clearTimeout});
  new vm.Script(app,{filename:"judge-site/src/app.js"}).runInContext(context);
  await until(()=>nodes.get("source-state").dataset.state==="PASS"&&nodes.get("saved-state").dataset.state==="PASS");
  return {trace,nodes,samples};
}
let checks=0;
async function test(name,fn){await fn();checks++;console.log("PASS "+name);}
await test("verdict is programmatically focusable and describes its result",async()=>{
  const a=await setup();assert.equal(a.nodes.get("verdict").getAttribute("tabindex"),"-1");assert.equal(a.nodes.get("verdict").getAttribute("aria-describedby"),"verdict-detail");assert.equal(a.trace.length,0,"Initial setup must not steal focus");
});
await test("primary CTA reveals computed wrong-pair result after busy clears",async()=>{
  const a=await setup();a.nodes.get("check-wrong").click();await until(()=>a.trace.length===2);
  assert.equal(a.nodes.get("verdict").textContent,"Repair rejected");assert.equal(a.nodes.get("candidate-total").textContent,"2.60");
  assert.equal(a.trace[0].kind,"focus");assert.equal(a.trace[0].id,"verdict");assert.equal(a.trace[0].options.preventScroll,true);assert.equal(a.trace[0].busy,"false");assert.equal(a.trace[0].verdict,"Repair rejected");
  assert.equal(a.trace[1].kind,"scroll");assert.equal(a.trace[1].id,"results");assert.equal(a.trace[1].options.behavior,"smooth");assert.equal(a.trace[1].options.block,"start");
});
await test("reduced-motion preference requests an immediate result reveal",async()=>{
  const a=await setup({reduced:true});a.nodes.get("check-wrong").click();await until(()=>a.trace.length===2);assert.equal(a.trace[1].options.behavior,"auto");
});
await test("sample selection waits for explicit check and reveals only the new outcome",async()=>{
  const a=await setup();a.nodes.get("check-wrong").click();await until(()=>a.trace.length===2);a.nodes.get("hold").click();a.samples[0].click();assert.equal(a.trace.length,2);assert.equal(a.nodes.get("download").disabled,true);
  await a.nodes.get("run").click();assert.equal(a.nodes.get("verdict").textContent,"Repair matches");assert.equal(a.trace.length,4);assert.equal(a.trace[2].verdict,"Repair matches");
  a.samples[2].click();await a.nodes.get("run").click();assert.equal(a.nodes.get("verdict").textContent,"More evidence needed");assert.equal(a.trace[4].verdict,"More evidence needed");assert.equal(a.nodes.get("candidate-total").textContent,"—");
  const rows=a.nodes.get("pair-table").children;
  assert.deepEqual(rows.map(row=>row.children[2].textContent),["0.70","0.65","0.75","UNKNOWN"]);
  assert.deepEqual(rows.map(row=>row.children[3].textContent),["MATCH","MATCH","MATCH","UNKNOWN"]);
  assert.equal(a.nodes.get("candidate-detail").textContent,"3 known pair values · fourth pair unknown");
});
await test("failed computation reveals a blocked result without enabling receipts",async()=>{
  const a=await setup({compute:async()=>{throw new Error("CONTROLLED_CHECK_FAILURE");}});a.nodes.get("check-wrong").click();await until(()=>a.trace.length===2);assert.equal(a.trace[0].verdict,"Check unavailable");assert.equal(a.trace[0].busy,"false");assert.equal(a.nodes.get("download").disabled,true);assert.equal(a.nodes.get("hold").disabled,true);assert.equal(a.nodes.get("run-note").textContent,"CONTROLLED_CHECK_FAILURE");
});
await test("repeated CTA during a pending calculation produces one reveal",async()=>{
  let release,calls=0;const gate=new Promise(resolve=>release=resolve);
  const a=await setup({compute:async(...args)=>{calls++;await gate;return engine.computeReview(...args);}});a.nodes.get("check-wrong").click();a.nodes.get("check-wrong").click();assert.equal(calls,1);assert.equal(a.trace.length,0);release();await until(()=>a.trace.length===2);assert.equal(calls,1);
});
console.log(JSON.stringify({checks,status:"PASS",scope:"Offline app-handler DOM contract; actual scrolling pixels, visual layout, screen-reader speech and browser downloads NOT_RUN.",browser_used:false,provider_calls:0}));
