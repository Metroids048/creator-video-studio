import {FB,C,LUT,makeOut,hash,ss,clamp,lerp} from './px.js';
import {CHARS,MAT,drawChar,scarfTail} from './sprites.js';
const S=await(await fetch('./story.json')).json();
const canvas=document.querySelector('canvas'),g=canvas.getContext('2d'),fb=new FB(),out=makeOut(canvas);
await document.fonts.load('44px StudioCN');
CHARS.arlo.sword=false;MAT.steel=[C.ink,C.night,C.navy,C.blue];
const ease=(t,a,b)=>ss(a,b,t),R=(x,y,w,h,c)=>fb.rect(x,y,w,h,c);
function cn(s,x,y,size=40,color='#ead4aa',align='center'){
 g.save();g.font=`${size}px StudioCN`;g.textAlign=align;g.textBaseline='middle';g.fillStyle=color;g.fillText(s,x,y);g.restore();
}
function sky(t){
 fb.gradV(0,0,320,180,[C.ink,C.night,C.dslate]);
 for(let i=0;i<65;i++){const x=Math.floor(hash(i,2)*320),y=Math.floor(hash(i,9)*92);if(hash(i,3)>.35||Math.floor(t*.7+i)%3)fb.px(x,y,C.silver);}
 fb.disc(269,25,11,C.sand);fb.disc(264,21,11,C.night);
}
function hero(x,y,t,pose,flip=false){
 const p=pose||`walk${Math.floor(t*8)%4}`,s=drawChar('arlo',p,{t,wind:.25});
 scarfTail(fb,x+(flip?2:-2),y-24,t,.35,flip?-1:1,10);fb.blit(s,Math.round(x)-s.ox,Math.round(y)-s.oy,flip);
}
function road(t){
 R(0,142,320,38,C.night);R(0,142,320,2,C.slate);R(0,157,320,2,C.dslate);
 for(let x=-10;x<340;x+=44)R(x,169,22,2,C.silver);
 for(let x=0;x<320;x+=10)R(x,147,8,1,C.dslate);
}
function tower(x,w,floors,t,active=false){
 const h=20+floors*4;R(x,142-h,w,h,C.dslate);R(x+2,142-h+2,w-4,h-2,C.night);
 for(let y=142-h+7;y<132;y+=10)for(let xx=x+5;xx<x+w-6;xx+=10){R(xx,y,5,6,hash(xx,y)>.7?C.tan:C.dslate);if(hash(xx,y)>.7)R(xx,y+5,5,1,C.brown);}
 R(x+w/2-8,118,16,24,C.umber);R(x+w/2-6,121,12,21,active?C.amber:C.dslate);R(x+w/2+3,130,1,1,C.yellow);
 if(active)for(let y=143;y<154;y++)R(x+w/2-6-(y-143),y,12+2*(y-143),1,C.brown);
}
function street(t,final=false){
 sky(t);road(t);tower(75,58,30,t,false);tower(209,73,15,t,final&&t>31);
 R(21,108,2,34,C.slate);R(17,108,11,2,C.steel);R(20,110,4,3,C.yellow);
 R(140,132,35,3,C.brown);R(143,135,2,7,C.slate);R(170,135,2,7,C.slate);
 if(!final){
  const busx=lerp(-115,0,ease(t,0,1.3))-ease(t,2.6,5.6)*130;
  R(busx,114,68,30,C.teal);R(busx+2,116,64,4,C.lime);for(let i=0;i<4;i++)R(busx+5+i*14,121,10,9,C.navy);
  R(busx+54,132,8,10,C.sand);fb.disc(busx+13,145,5,C.ink);fb.disc(busx+54,145,5,C.ink);fb.disc(busx+13,145,2,C.silver);fb.disc(busx+54,145,2,C.silver);
  if(t>1.5){const x=lerp(55,104,ease(t,1.5,4.8));hero(x,143,t,t>4.8?'back':'walk'+Math.floor(t*8)%4);}
 }else{
  const x=lerp(104,246,ease(t,27.8,31.6)),walking=t<31.6;
  if(t<32.2)hero(x,143,t,walking?null:'back');
  if(t>33){const a=clamp((t-33)/.8,0,1);R(200,64,90,20,C.night);for(let i=0;i<Math.floor(10*a);i++)R(205+i*8,76,6,3,C.lime);}
 }
 out.present(fb,LUT.full);out.show();cn('A座',624,657,32,'#c0cbdc');cn('B座 · 101',1476,657,32,'#fee761');
 if(final&&t>33)cn('步数 +10,000',1470,414,32,'#63c74d');
}
function lift(t){
 R(0,0,320,180,C.night);R(0,20,320,128,C.dslate);for(let x=0;x<320;x+=40)R(x,20,1,128,C.slate);
 R(122,42,80,107,C.ink);R(127,49,70,98,C.steel);R(161,49,1,98,C.dslate);R(143,28,38,14,C.ink);
 R(210,74,7,24,C.umber);R(212,80,3,3,t>7.5?C.hot:C.silver);R(212,89,3,3,C.silver);
 // Two diagonal strips make the out-of-order barrier part of the elevator.
 for(let x=128;x<195;x++){R(x,87+(x-128)*.24,3,5,C.amber);R(x,111-(x-128)*.24,3,5,C.amber);}
 R(0,149,320,31,C.umber);for(let x=0;x<320;x+=24)R(x,150,1,30,C.brown);
 const x=lerp(75,106,ease(t,5.6,7.6));hero(x,150,t,t<7.6?null:'lookup');
 out.present(fb,LUT.full);out.show();cn(t<8?'42':'故障',972,210,48,t<8?'#fee761':'#ff0044');
 if(t>9)cn('请走楼梯 →',1510,472,38,'#fee761');
}
function stairs(t){
 const u=ease(t,11.8,20.9),level=Math.min(42,1+Math.floor(u*41)),stride=(t-11.6)*2.4,step=Math.floor(stride),phase=stride-step;
 R(0,0,320,180,C.ink);R(34,0,252,180,C.night);
 // Follow one continuous flight: the tread under the avatar and its feet
 // share the same height; the floor counter supplies the time compression.
 for(let i=step-9;i<step+12;i++){
  const x=145+(i-stride)*20,y=103-(i-stride)*4;
  R(x,y,21,4,C.steel);R(x,y+4,21,76,C.dslate);R(x,y+4,1,76,C.slate);
 }
 fb.line(36,88+phase*4,286,38+phase*4,C.silver);
 for(let i=0;i<3;i++){R(12,24+i*63,14,27,C.navy);R(14,26+i*63,10,23,C.dslate);}
 const y=103+phase*4;hero(145,y,t,`walk${Math.floor(phase*4)}`);
 // Floor number accelerates, then stops; the avatar remains on a stair tread.
 R(221,12,48,22,C.ink);out.present(fb,LUT.full);out.show();cn(`${level} F`,1470,132,64,'#fee761');
 if(t>19.5)cn('体力 01 / 100',570,126,32,'#ff0044');
}
function door(t){
 R(0,0,320,180,C.night);R(0,27,320,121,C.dslate);R(0,148,320,32,C.umber);
 R(180,42,63,107,C.umber);R(185,46,53,102,C.brown);R(189,50,45,36,C.dbrown);R(189,92,45,49,C.dbrown);fb.disc(232,97,2,C.amber);
 const x=lerp(75,153,ease(t,21.6,23.5));hero(x,150,t,t<23.5?null:'grip');
 R(194,29,36,12,C.umber);R(29,29,71,74,C.ink);R(33,33,63,66,C.navy);
 out.present(fb,LUT.full);out.show();cn('A座 4201',1270,208,30,'#ead4aa');
 if(t>24){g.fillStyle='#181425';g.fillRect(210,260,500,270);g.strokeStyle='#c0cbdc';g.lineWidth=5;g.strokeRect(210,260,500,270);cn('你的地址',460,315,34,'#8b9bb4');cn('B座 101',460,412,60,'#fee761');cn('？！',935,450,68,'#ff0044');}
}
function render(t){
 if(t<5.6)street(t);else if(t<11.6)lift(t);else if(t<21.6)stairs(t);else if(t<27.4)door(t);else street(t,true);
 // A stable subtitle band keeps Chinese readable without blurring the pixel scene.
 g.fillStyle='rgba(24,20,37,.91)';g.fillRect(0,930,1920,150);
 for(const c of S.captions)if(t>=c.start&&t<c.end)cn(c.text,960,1000,44,'#ead4aa');
 cn(S.title,86,66,30,'#ead4aa','left');
}
window.DUR=S.duration;window.render=render;window.SUBS=S.captions;window.READY=true;
