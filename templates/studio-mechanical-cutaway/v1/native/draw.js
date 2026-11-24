export const C=document.querySelector('canvas'),ctx=C.getContext('2d'),W=1280,H=720;
export const S=await (await fetch('story.json')).json();
export const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
export const ease=v=>{v=clamp(v);return v*v*(3-2*v)};
export const lerp=(a,b,t)=>a+(b-a)*t;
export const phase=(t,a,b)=>ease((t-a)/(b-a));
export function bg(c){ctx.globalAlpha=1;ctx.fillStyle=c;ctx.fillRect(0,0,W,H)}
export function text(s,x,y,size=28,color='#222',align='left',weight=500){ctx.fillStyle=color;ctx.font=`${weight} ${size}px Studio`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillText(s,x,y)}
export function line(x,y,a,b,color='#222',width=2){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(a,b);ctx.stroke()}
export function circle(x,y,r,c){if(r<=0)return;ctx.fillStyle=c;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill()}
export function box(x,y,w,h,c,r=0){ctx.fillStyle=c;ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill()}
export function poly(pts,c){ctx.fillStyle=c;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill()}
export function label(t,color='#222'){text(S.title,56,40,18,color);text(S.category,1224,40,13,color,'right');line(56,65,1224,65,color,0.5);let i=S.scenes.findLastIndex(s=>t>=s.start);i=Math.max(i,0);text(S.scenes[i].text,640,671,23,color,'center');line(56,705,56+1168*t/S.duration,705,color,2)}
export function eyes(x,y,s=1,look=0){circle(x-13*s+look,y,4*s,'#181c23');circle(x+13*s+look,y,4*s,'#181c23')}
export function person(x,y,scale=1,coat='#bd6551',pose=0){ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);line(-7,0,-14+pose*8,35,'#344348',8);line(7,0,14-pose*8,35,'#344348',8);box(-19,-62,38,67,coat,12);circle(0,-81,19,'#ecc5a0');poly([[-20,-87],[-12,-104],[12,-103],[23,-88],[12,-90],[6,-97],[-6,-89]],'#293841');circle(-5,-82,1.6,'#283138');circle(7,-82,1.6,'#283138');line(-16,-48,-28,-21,'#ecc5a0',7);line(16,-48,27,-21,'#ecc5a0',7);ctx.restore()}
export function rng(seed){let v=seed>>>0;return()=>{v=(1664525*v+1013904223)>>>0;return v/4294967296}}
export function grain(seed=41,alpha=.045){const r=rng(seed);ctx.save();ctx.globalAlpha=alpha;for(let i=0;i<3000;i++)circle(r()*W,r()*H,.3+r()*1.2,r()>.5?'#fff':'#352e24');ctx.restore()}
export async function ready(fn){await document.fonts.load('500 28px Studio');window.DUR=S.duration;window.render=t=>{ctx.save();fn(Math.max(0,Math.min(t,S.duration-1/30)));ctx.restore()};window.READY=true;window.render(0)}
