import test from 'node:test';
import assert from 'node:assert/strict';
import {queueSOS,readOutbox,flushSOS,saveSnapshot,readSnapshot} from '../web/lib/offline.mjs';
const storage=()=>{const map=new Map();return {getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v)};};
test('lost response keeps original id and packet; successful retry strips private content',async()=>{
 const s=storage(); const p={request_id:'request-1',message:'private',lat:10,lon:20};
 queueSOS(s,p);queueSOS(s,p);assert.equal(readOutbox(s).length,1);
 await flushSOS(s,async()=>{throw Error('offline')});assert.deepEqual(readOutbox(s)[0].packet,p);
 await flushSOS(s,async received=>{assert.deepEqual(received,p);return {id:'SOS-1',status:'QUEUED'}});
 assert.equal(readOutbox(s)[0].receiptId,'SOS-1');assert.equal(readOutbox(s)[0].packet,undefined);
});
test('snapshot excludes private SOS records and missions',()=>{
 const s=storage();saveSnapshot(s,{nodes:[],incidents:[],sos:[{message:'private'}],missions:[{note:'private'}]});
 assert.deepEqual(readSnapshot(s).data.sos,[]);assert.deepEqual(readSnapshot(s).data.missions,[]);
});
test('malformed storage recovers to empty state',()=>{
 const s={getItem:()=>'{broken'};assert.deepEqual(readOutbox(s),[]);assert.equal(readSnapshot(s),null);
});
test('incomplete server response never marks request received',async()=>{
 const s=storage();queueSOS(s,{request_id:'r'});const result=await flushSOS(s,async()=>({}));assert.ok(result.error);assert.equal(readOutbox(s)[0].status,'LOCAL_PENDING');
});
import {updateReceipts} from '../web/lib/offline.mjs';
test('operator acknowledgement survives a later offline reload',async()=>{
 const s=storage();queueSOS(s,{request_id:'r'});await flushSOS(s,async()=>({id:'SOS-2',status:'QUEUED'}));
 updateReceipts(s,[{id:'SOS-2',status:'ACKNOWLEDGED'}]);assert.equal(readOutbox(s)[0].status,'ACKNOWLEDGED');
});
