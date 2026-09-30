export const MAP_W = 1000,
  MAP_H = 620;
export function groundHeight(x, y) {
  return (
    14 +
    22 * Math.sin(x / 157) * Math.cos(y / 119) +
    12 * Math.sin((x + y) / 83)
  );
}
export function nodePoint(node) {
  return [
    100 + Math.max(0, Math.min(100, Number(node.x) || 0)) * 8,
    110 + Math.max(0, Math.min(100, Number(node.y) || 0)) * 4,
  ];
}
export function projectPoint(
  x,
  y,
  z = 0,
  { cut = false, yaw = 0, zoom = 1, pan = { x: 0, y: 0 } } = {},
) {
  if (!cut) {
    const angle = ((yaw || 0) * Math.PI) / 180,
      dx = x - 500,
      dy = y - 310,
      rx = dx * Math.cos(angle) - dy * Math.sin(angle),
      ry = dx * Math.sin(angle) + dy * Math.cos(angle);
    return [500 + rx * zoom + pan.x, 310 + ry * zoom + pan.y];
  }
  const angle = (yaw * Math.PI) / 180,
    dx = x - 500,
    dy = y - 310;
  return [
    500 + (dx * Math.cos(angle) - dy * Math.sin(angle)) * 0.91,
    285 + (dx * Math.sin(angle) + dy * Math.cos(angle)) * 0.53 - z * 0.7,
  ];
}
export function layoutLabels(markers) {
 const boxes=[];const result={};const w=133,h=57,padding=8;
 const intersects=(a,b)=>a.x<b.x+b.w+padding&&a.x+a.w+padding>b.x&&a.y<b.y+b.h+padding&&a.y+a.h+padding>b.y;
 for(const marker of markers){
  const candidates=[[28,-29],[28,24],[-161,-29],[-161,24],[28,-88],[-161,-88],[0,48],[28,83]].map(([dx,dy])=>({x:Math.max(12,Math.min(855,marker.x+dx)),y:Math.max(90,Math.min(510,marker.y+dy)),w,h}));
  const score=b=>boxes.filter(a=>intersects(a,b)).length*1000+markers.filter(m=>intersects({x:m.x-17,y:m.y-17,w:34,h:34},b)).length*100;
  candidates.sort((a,b)=>score(a)-score(b));const best=candidates[0];boxes.push(best);result[marker.id]=best;
 }
 return result;
}
