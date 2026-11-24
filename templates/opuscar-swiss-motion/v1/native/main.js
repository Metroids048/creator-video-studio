import {clamp,lerp,snap,lin,E} from './ease.js';
const S=await fetch('story.json').then(r=>r.json());await document.fonts.load('48px Studio');
const g=document.querySelector('canvas').getContext('2d'),C={paper:'#eae9e5',ink:'#111111',red:'#e30613',grid:'#cfcec9'};
const M=100,CW=142,RH=110;
const tasks=[['写方案',0,0,4,1],['回消息',4,0,3,0],['开会',7,0,5,0],['做原型',0,1,5,1],['同步',5,1,4,0],['补材料',9,1,3,0],['验结果',0,2,4,1],['临时会',4,2,4,0],['再同步',8,2,4,0],['追进度',0,3,6,0],['改格式',6,3,6,0]];
const captions=[['排得满，不代表做得完。',.7,5.7],['先留下三件真正要紧的事。',6.4,12.6],['把重要事项，排进专注的时间。',13.4,19.5],['给突然发生的事，留一个位置。',20.5,26],['留白，也是安排的一部分。',27,31.8]];
function txt(s,x,y,size=42,col=C.ink,align='left'){g.font=`${size}px Studio`;g.textAlign=align;g.textBaseline='middle';g.fillStyle=col;g.fillText(s,x,y);}
function rect(x,y,w,h,col){g.fillStyle=col;g.fillRect(x,y,w,h);}
function render(t){
 g.setTransform(1,0,0,1,0,0);g.globalAlpha=1;rect(0,0,1920,1080,C.paper);
 const final=snap(t,27.3,1.1),scale=lerp(1,.82,final);g.save();g.translate(lerp(0,165,final),lerp(0,55,final));g.scale(scale,scale);
 txt('给时间',M,124,88);txt('留白',M+470,124,88,C.red);txt('A DAY WITH SPACE',M,205,25);
 const chapter=t<6?'01 / 排满':t<13?'02 / 取舍':t<20?'03 / 对齐':'04 / 缓冲';txt(chapter,1800,123,30,C.ink,'right');
 const gy=320;
 g.strokeStyle=C.grid;g.lineWidth=1;
 for(let i=0;i<=12;i++){g.beginPath();g.moveTo(M+i*CW,gy);g.lineTo(M+i*CW,gy+RH*4);g.stroke();}
 for(let j=0;j<=4;j++){g.beginPath();g.moveTo(M,gy+j*RH);g.lineTo(M+12*CW,gy+j*RH);g.stroke();}
 ['09:00','11:00','14:00','16:00'].forEach((s,i)=>txt(s,M-10,gy+i*RH-20,25));
 tasks.forEach(([label,col,row,w,keep],i)=>{
  const p=snap(t,.8+i*.32,.30);if(!p)return;
  const remove=keep?0:snap(t,7.4+i*.18,.35);if(remove>=1)return;
  const reflow=keep?snap(t,14+i*.20,1):0;
  const index=[0,3,6].indexOf(i),targetCol=1+index*4;
  const x=lerp(M+col*CW,M+targetCol*CW,reflow),y=lerp(gy+row*RH,gy+RH,reflow);
  const width=lerp(w*CW-8,3*CW-8,reflow),height=(RH-8)*p;
  rect(x,y,width*(1-remove),height,keep&&t>6?C.red:C.ink);
  if(width*(1-remove)>150)txt(label,x+20,y+height/2,34,C.paper);
  if(!keep&&t>6.5+i*.18&&remove<1)rect(x,y+50,width*snap(t,7+i*.18,.2),4,C.paper);
 });
 // The seventh task cannot fit. It physically pushes beyond the grid.
 if(t>4.3&&t<7){const k=snap(t,5,.5);rect(M+1500,gy+460,220+k*70,74,C.red);txt('又来一件',M+1520,gy+497,27,C.paper);}
 if(t>16){
  const a=snap(t,18,.65);g.save();g.globalAlpha=a;g.setLineDash([12,8]);g.strokeStyle=C.red;g.lineWidth=3;g.strokeRect(M+CW,gy+2.5*RH,10*CW-8,RH);g.setLineDash([]);txt('缓冲区',M+CW+24,gy+3*RH,36,C.red);g.restore();
 }
 if(t>20){
  const k=E(lin(t,20,23)),x=lerp(1770,1300,k),y=lerp(222,gy+3*RH,k);
  g.fillStyle=C.red;g.beginPath();g.arc(x,y,31,0,Math.PI*2);g.fill();
  if(t>23.4)txt('有变化，也放得下。',M+CW,gy+4.35*RH,39);
 }
 g.restore();
 if(t>28){rect(1540,220,4,630,C.red);txt('为变化',1590,690,40);txt('留一格。',1590,752,40,C.red);}
 rect(0,935,1920,145,C.ink);for(const[s,a,b]of captions)if(t>=a&&t<b)txt(s,960,1005,43,C.paper,'center');
}
window.render=render;window.DUR=S.duration;window.SUBS=captions;window.READY=true;
