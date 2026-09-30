import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {predictChannel,demoReading} from '../web/lib/forecast.mjs';
const model=JSON.parse(readFileSync(new URL('../web/public/models/short-horizon.json',import.meta.url),'utf8'));
const history=Array.from({length:60},(_,i)=>demoReading('D',i,Date.parse('2026-09-28T00:00:00Z')));
test('trained artifact forecasts exactly 20 seconds beyond the latest sample with ordered finite bands',()=>{
 for(const key of ['tilt_deg','vibration','temperature_c','humidity_pct','pressure_hpa']){
  const p=predictChannel(history,key,model);assert.equal(p.available,true);
  assert.equal(p.points.at(-1).time-Date.parse(history.at(-1).sample_time),20000);
  for(const v of p.points){assert.ok(Number.isFinite(v.value));assert.ok(v.lower<=v.value&&v.value<=v.upper);}
 }
});
test('missing, stale, mixed, invalid and irregular data never silently receive a forecast',()=>{
 for(const modify of [r=>({...r,valid:false}),r=>({...r,stale:true}),r=>({...r,tilt_deg:null}),r=>({...r,session_id:'different'}),r=>({...r,sample_time:'bad'}),r=>({...r,sample_time:new Date(Date.parse(r.sample_time)+60000).toISOString()})]){
  const h=history.map(r=>({...r}));h[55]=modify(h[55]);assert.equal(predictChannel(h,'tilt_deg',model).available,false);
 }
 assert.equal(predictChannel(history.slice(0,6),'tilt_deg',model).available,false);
 assert.equal(predictChannel(history,'ir',model).available,false);
 assert.equal(predictChannel(history,'tilt_deg',null).available,false);
});
test('MQ5 forecasts wait for warm-up and discrete IR is not extrapolated',()=>{
 const h=Array.from({length:60},(_,i)=>demoReading('C',i,0));
 assert.equal(predictChannel(h,'gas_raw',model).available,true);
 h.at(-1).gas_ready=false;assert.equal(predictChannel(h,'gas_raw',model).available,false);
 assert.equal(predictChannel(h,'ir',model).available,false);
});
test('benchmark is synthetic-only and model beats a persistence baseline on held-out generated sessions',()=>{
 assert.match(model.report.training_scope,/synthetic/);assert.equal(model.operational_warnings,false);
 assert.ok(model.report.test_mae_normalized[3]<model.report.persistence_mae_normalized[3]);
});
