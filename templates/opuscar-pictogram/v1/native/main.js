const S=await fetch('story.json').then(r=>r.json());
await document.fonts.load('44px Studio');
const c=document.querySelector('canvas'),g=c.getContext('2d'),{clamp,lerp,E,PAL}=G;
const move=(t,a,b)=>E.io3(clamp((t-a)/(b-a)));
const caps=[['今天的雨，来得有点突然。',.8,5],['有伞的人，停了一步。',6,10.7],['把自己的晴天，分出一半。',11.7,17.6],['路还是那条路，雨却小了。',18.7,25.5],['原来，温暖可以一起抵达。',27,31.8]];
function text(s,x,y,size=48,col=G.CREAM,align='center'){g.fillStyle=col;g.font=`${size}px Studio`;g.textAlign=align;g.textBaseline='middle';g.fillText(s,x,y);}
function person(x,y,t,col,walk=0,reach=0,hold=null){
 G.disc(g,x,y-235,43,col);G.seg(g,[x,y-174],[x,y-78],65,col);
 const k=Math.sin(t*7)*walk;
 G.seg(g,[x-14,y-80],[x-35+k*27,y],26,col);G.seg(g,[x+14,y-80],[x+35-k*27,y],26,col);
 G.seg(g,[x-28,y-160],[x-54-k*12,y-91],22,col);
 G.seg(g,[x+25,y-160],hold||[x+60+reach*35,y-128-reach*60],22,col);
}
function rain(t,ux=null,open=0){
 for(let i=0;i<78;i++){
  const x=(i*137+t*65)%1920,y=(i*211+t*355)%870;
  // The shelter is spatially tied to the actual canopy, not a separate effect.
  if(ux!==null&&Math.abs(x-ux)<240*open&&y>485)continue;
  G.seg(g,[x,y],[x-12,y+35],5,'#7ab6da');
 }
}
const pat=G.pattern('yellow',93,{set:'sun',density:.62,spread:.8});
function render(t){
 g.setTransform(1,0,0,1,0,0);g.globalAlpha=1;
 let bg=t<5?'#13254a':t<11?'#00544c':t<18?'#1a3263':'#24457d';
 g.fillStyle=bg;g.fillRect(0,0,1920,1080);
 const stage=Math.min(4,Math.floor([0,5,11,18,26].filter(v=>t>=v).length-1));
 text('两个人的晴天',100,100,38,G.CREAM,'left');text(`0${stage+1} / 05`,1810,100,30,G.CREAM,'right');
 G.hair(g,100,154,1720,'#5d7cad',1,2);G.hair(g,100,154,1720,G.CREAM,t/32,5);
 if(t<26){
  g.fillStyle=G.rgba('#5d7cad',.25);g.fillRect(0,840,1920,55);
  let x1=620,x2=t<5?2030:lerp(1530,1000,move(t,5.3,9.3)),ux=x2,op=1;
  if(t<5){G.cloud(g,960,350,180,'#5d7cad');rain(t);person(x1,840,t,G.CREAM,0);}
  else{
   if(t>=11){ux=lerp(x2,810,move(t,11.2,15.2));x2=lerp(1000,950,move(t,11.2,15.2));}
   if(t>=18){const shift=lerp(0,440,move(t,18.2,24.8));x1+=shift;x2+=shift;ux+=shift;}
   rain(t,ux,op);person(x1,840,t,G.CREAM,t>18?1:0,t>13?.25:0);
   person(x2,840,t,'#b8daeb',t<9||t>18?1:0,1,[ux,700]);
   G.umbrella(g,ux,493,270,op,0,G.UMB,G.UMB2,G.CREAM);
   if(t<10.6)text('…',x1,470,58);
   if(t>21){
    G.rrect(g,1510,360,320,34,5,G.CREAM);G.seg(g,[1550,394],[1550,839],20,G.CREAM);G.seg(g,[1790,394],[1790,839],20,G.CREAM);
    text('车站',1670,325,38);G.rrect(g,1575,756,180,18,7,G.CREAM);
   }
  }
 }else{
  G.drawPattern(g,pat,j=>move(t,26,27.1)*(j%2?110:-110));
  g.fillStyle='#f2ba1d';g.fillRect(300,260,1320,530);
  person(790,790,t,'#231902',0,.7);person(1130,790,t,'#231902',0,.7,[960,670]);
  G.umbrella(g,960,459,270,1,0,'#fbf6ec','#f9d87e','#231902');
 }
 g.fillStyle=t>=26?'#231902':bg;g.fillRect(0,930,1920,150);
 for(const [s,a,b]of caps)if(t>=a&&t<b)text(s,960,1000,46);
}
window.DUR=S.duration;window.render=render;window.READY=true;window.SUBS=caps;
