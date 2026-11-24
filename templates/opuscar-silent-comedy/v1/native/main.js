import {FilmPost,damage} from './engine/film.js';
import {Redraw} from './engine/redraw.js';
import {intertitle,iris,theatre} from './engine/cards.js';
const S=await fetch('story.json').then(r=>r.json());await document.fonts.load('80px Studio');
const canvas=document.querySelector('canvas'),g=canvas.getContext('2d'),src=document.createElement('canvas');src.width=1440;src.height=1080;
const q=src.getContext('2d'),FP=new FilmPost(1440,1080),RD=new Redraw(1440,1080),clamp=x=>Math.max(0,Math.min(1,x)),ease=x=>{x=clamp(x);return x*x*(3-2*x)};
function line(points,w=8,col='#282520'){q.strokeStyle=col;q.lineWidth=w;q.lineCap='round';q.lineJoin='round';q.beginPath();points.forEach(([x,y],i)=>i?q.lineTo(x,y):q.moveTo(x,y));q.stroke();}
function box(x,y,w,h,col='#b7aea0'){q.fillStyle=col;q.fillRect(x,y,w,h);q.strokeStyle='#39342b';q.lineWidth=7;q.strokeRect(x,y,w,h);}
function glasses(x,y){q.strokeStyle='#201d18';q.lineWidth=9;q.beginPath();q.ellipse(x-34,y,28,21,0,0,7);q.ellipse(x+34,y,28,21,0,0,7);q.moveTo(x-6,y-4);q.lineTo(x+6,y-4);q.stroke();}
function person(x,y,t,{arm=0,down=0,walk=0,smile=0,flip=1,hand=null}={}){
 q.save();q.translate(x,y);q.scale(flip,1);
 const step=Math.sin(t*8)*walk;
 line([[-23,-135],[-40-step*18,-44],[-53-step*15,0]],24);line([[23,-135],[35+step*18,-44],[50+step*15,0]],24);
 box(-60,-12,67,20,'#282520');box(16,-12,67,20,'#282520');
 q.fillStyle='#514b41';q.beginPath();q.moveTo(-48,-290);q.lineTo(48,-290);q.lineTo(70,-132);q.lineTo(-65,-132);q.closePath();q.fill();
 q.fillStyle='#e5ded0';q.beginPath();q.ellipse(0,-352,66,85,-.05,0,7);q.fill();q.strokeStyle='#39342b';q.lineWidth=6;q.stroke();
 line([[-65,-385],[-40,-433],[30,-438],[61,-396]],17);
 q.fillStyle='#29251e';for(const xx of [-22,23]){q.beginPath();q.ellipse(xx,-350,5,7,0,0,7);q.fill();}
 line([[-12,-312],[0,-307-smile*10],[18,-314]],5);
 glasses(0,-417+down*66);
 line([[-43,-271],[-90,-215-arm*70],[-130+arm*112,-202-arm*185]],18);
 const rh=hand?[(hand[0]-x)/flip,hand[1]-y]:[129-arm*113,-204-arm*177];
 line([[43,-271],[(43+rh[0])*.5+18,(-271+rh[1])*.5+20],rh],18);
 q.fillStyle='#ddd3c0';for(const [xx,yy]of [[-130+arm*112,-202-arm*185],rh]){q.beginPath();q.arc(xx,yy,14,0,7);q.fill();}
 q.restore();
}
function room(t){
 q.fillStyle='#ddd4c4';q.fillRect(0,0,1440,1080);q.fillStyle='#c7bca7';q.fillRect(0,790,1440,290);
 for(let x=-100;x<1500;x+=100)line([[x,790],[x-230,1080]],2,'#968a76');line([[0,790],[1440,790]],6);
 box(110,265,250,310,'#b4a794');box(125,280,220,280,'#e4dccd');line([[235,282],[235,555]],5);line([[125,420],[345,420]],5);
 box(1130,280,170,310,'#ab9d85');q.fillStyle='#e0d7c5';q.fillRect(1143,294,144,280);
}
function card(text,sub,t){intertitle(q,1440,1080,{level:1,lines:[{text,font:'Studio',size:88},{text:sub,font:'Studio',size:36}],gap:1.6},t);}
function render(t){
 const ta=Math.floor(t*16)/16;room(ta);
 if(t<3)card('眼镜去哪了','一场发生在头顶的悬案',t);
 else if(t<10){
  box(520,690,610,32,'#8e816b');box(555,722,28,200,'#766951');box(1055,722,28,200,'#766951');
  const p=ease((ta-4)/1),lift=Math.sin(clamp((ta-5.5)/2.5)*Math.PI)*110;
  person(430,925,ta,{hand:[580,665-lift]});
  q.save();q.translate(660,665-lift);box(-90,-20,180,25,'#eee6d5');line([[0,-20],[0,5]],3);q.restore();
  if(t>7.8){q.font='80px Studio';q.fillStyle='#282520';q.fillText('？',350,330);}
 }else if(t<12.5)card('一定在沙发里','我明明，刚刚还戴着。',t-10);
 else if(t<20){
  box(710,655,470,190,'#91836d');box(670,590,70,275,'#7c6d57');box(1150,590,70,275,'#7c6d57');
  box(750,560,180,110,'#b7a88e');const lift=Math.sin(clamp((ta-13.8)/4.8)*Math.PI)*175;
  q.save();q.translate(1030,690-lift);box(-100,-15,200,45,'#bcac91');q.restore();
  person(760,925,ta,{hand:[934,695-lift]});
 }else if(t<22)card('凶手，就在眼前','先，看看自己。',t-20);
 else if(t<29.8){
  box(805,230,400,590,'#5d5341');box(824,250,362,546,'#d1ccc0');
  const walk=ease((ta-22)/1.5),down=ease((ta-25)/1.0),arm=ease((ta-24.2)/.7)*(1-ease((ta-26)/.7));
  q.save();q.beginPath();q.rect(824,250,362,546);q.clip();person(1025,917,ta,{arm,down,smile:down,flip:-1});q.restore();
  person(610+walk*90,925,ta,{arm,down,walk:t<23.5?1:0,smile:down});
  if(t>23.5&&t<25){q.font='70px Studio';q.fillStyle='#282520';q.fillText('！',700,360);}
  if(t>29)iris(q,1440,1080,700,570,1600*(1-ease((t-29)/.8)),4);
 }else card('原来，一直都在。','THE END',t-29.8);
 const frame=Math.floor(t*24),isCard=t<3||(t>=10&&t<12.5)||(t>=20&&t<22)||t>=29.8;
 const drawn=isCard?src:RD.render(src,{frame,levels:5,hatch:.6,lines:.65});
 const film=FP.render(drawn,{frame,strength:.35,sepia:.22,grain:.75,scratches:.4,halation:.7,weave:.5});
 theatre(g,1920,1080,{x:240,y:0,w:1440,h:1080},.45,1);g.drawImage(film,240,0);damage(g,240,0,1440,1080,frame,.28);
}
window.render=render;window.DUR=S.duration;window.SUBS=[];window.READY=true;
