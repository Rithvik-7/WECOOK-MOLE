import test from 'node:test';
import assert from 'node:assert/strict';
import {nodePoint,projectPoint,groundHeight,layoutLabels} from '../web/lib/map-geometry.mjs';
const nodes=[{id:'A',x:28,y:42},{id:'B',x:48,y:38},{id:'C',x:62,y:58},{id:'D',x:74,y:34}];
function intersect(a,b){return a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;}
test('cutaway markers and labels remain in bounds and separated through rotation',()=>{
 for(const yaw of [-20,-12,-10,0,10,20,28]){
  const markers=nodes.map(n=>{const [gx,gy]=nodePoint(n);const [x,y]=projectPoint(gx,gy,groundHeight(gx,gy),{cut:true,yaw});return {id:n.id,x,y};});
  const labels=Object.values(layoutLabels(markers));
  labels.forEach((a,i)=>{assert.ok(a.x>=0&&a.x+a.w<=1000&&a.y>=0&&a.y+a.h<=620);labels.slice(i+1).forEach(b=>assert.equal(intersect(a,b),false,`overlap at ${yaw}`));});
 }
});
test('surface projection supports reversible zoom and pan',()=>{
 const [x,y]=nodePoint(nodes[0]);assert.deepEqual(projectPoint(x,y),[x,y]);
 const zoom=projectPoint(x,y,0,{zoom:1.6,pan:{x:80,y:-20}});assert.equal(zoom[0],500+(x-500)*1.6+80);assert.equal(zoom[1],310+(y-310)*1.6-20);
});
