import {buildPath,headAt,posAt} from './geom.js';
import {prepare,drawLine,drawBlots} from './ink.js';
import {makePaper,drawPaper,makeTooth,drawTooth,vignette} from './paper.js';
import {clamp,ss,lerp} from '/core/lib.js';
const S=await (await fetch('./story.json')).json();
const cv=document.querySelector('canvas'),ctx=cv.getContext('2d'),W=cv.width,H=cv.height;
await document.fonts.load('42px StudioSerif');
const P=prepare(buildPath(S.segments)),paper=makePaper(),tooth=makeTooth();
function camera(t){const a=S.camera.findLast(k=>k.t<=t)||S.camera[0];const b=S.camera.find(k=>k.t>a.t)||a;const u=ss(clamp((t-a.t)/Math.max(.001,b.t-a.t)));return {cx:lerp(a.x,b.x,u),cy:lerp(a.y,b.y,u),k:lerp(a.k,b.k,u),r:0};}
function text(s,x,y,size,alpha=1,align='center'){ctx.save();ctx.globalAlpha=alpha;ctx.font=`${size}px StudioSerif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.lineJoin='round';ctx.lineWidth=12;ctx.strokeStyle='rgba(244,239,228,.93)';ctx.strokeText(s,x,y);ctx.fillStyle='#362e27';ctx.fillText(s,x,y);ctx.restore();}
function render(t){
 const cam=camera(t),M=(x,y)=>[W/2+(x-cam.cx)*cam.k,H/2+(y-cam.cy)*cam.k];
 drawPaper(ctx,paper,cam,W,H);const head=headAt(P,t);if(t>=P.T[0])drawLine(ctx,P,head,M,cam.k);drawBlots(ctx,P,t,M,cam.k);drawTooth(ctx,tooth,cam,W,H);vignette(ctx,W,H);
 if(t>=.8 && t<33.1){const [x,y]=M(...posAt(P,head));ctx.save();ctx.fillStyle='#a35936';ctx.shadowColor='rgba(90,45,20,.3)';ctx.shadowBlur=15;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();ctx.restore();}
 const a=clamp((t-29.6)/1.2);if(a>0){const [x,y]=M(598,-62);ctx.save();ctx.globalAlpha=a*.58;ctx.fillStyle='#d6a551';ctx.fillRect(x,y,59*cam.k,74*cam.k);ctx.restore();}
 text(S.title,110,105,46,.8,'left');text('一笔，走完一段想念',1810,105,28,.65,'right');
 for(const c of S.captions){if(t>=c.start&&t<c.end+.3){const a=Math.min(clamp((t-c.start)/.35),1-clamp((t-c.end)/.3));text(c.text,W/2,H-115,44,a);}}
 const e=S.ending;if(t>=e.start){text(e.text,W/2,775,58,clamp((t-e.start)/1));text(S.subtitle,W/2,858,32,clamp((t-e.start-.65)/1)*.75);}
}
window.DUR=S.duration;window.render=render;window.SUBS=S.captions;window.PATH=P;window.READY=true;
