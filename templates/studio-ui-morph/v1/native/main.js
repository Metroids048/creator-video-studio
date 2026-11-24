const S = await fetch('story.json').then(r => r.json());
await document.fonts.load('32px Studio');
const canvas = document.querySelector('canvas'), g = canvas.getContext('2d');
const W=1280,H=720, ink='#142922',muted='#74837d',green='#78c6a3';
const clamp=x=>Math.max(0,Math.min(1,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
const lerp=(a,b,p)=>a+(b-a)*p;
function rr(x,y,w,h,r,fill,stroke){g.beginPath();g.roundRect(x,y,w,h,Math.min(r,w/2,h/2));if(fill){g.fillStyle=fill;g.fill();}if(stroke){g.strokeStyle=stroke;g.lineWidth=1.5;g.stroke();}}
function text(s,x,y,size=24,color=ink,align='center'){g.font=`${size}px Studio`;g.fillStyle=color;g.textAlign=align;g.textBaseline='middle';g.fillText(s,x,y);}
function line(x,y,a,b,color=ink,width=2){g.beginPath();g.moveTo(x,y);g.lineTo(a,b);g.lineWidth=width;g.strokeStyle=color;g.lineCap='round';g.stroke();}
function arc(x,y,r,a,b,color,width){g.beginPath();g.arc(x,y,r,a,b);g.lineWidth=width;g.strokeStyle=color;g.lineCap='round';g.stroke();}
function check(x,y,scale=1){g.save();g.translate(x,y);g.scale(scale,scale);g.beginPath();g.moveTo(-15,0);g.lineTo(-3,12);g.lineTo(20,-15);g.strokeStyle=green;g.lineWidth=5;g.lineCap='round';g.lineJoin='round';g.stroke();g.restore();}
function contents(k,t,alpha){if(alpha<.001)return;g.save();g.globalAlpha=alpha;g.translate(640,365);const item=S.states[k];
 switch(item.kind){
 case 'button': text(item.label,0,0,25,'#f4fff9');line(110,0,124,0,'#f4fff9',2);line(119,-5,124,0,'#f4fff9');line(119,5,124,0,'#f4fff9');break;
 case 'loader':arc(-62,0,11,t*4,t*4+4.4,green,3);text(item.label,19,0,22,'#f4fff9');break;
 case 'check':check(-55,0,.7);text(item.label,16,0,23,'#f4fff9');break;
 case 'timer':
  rr(-170,-100,40,40,12,'#e7f3ec');text('写',-150,-80,18);text(item.label,-110,-80,22,ink,'left');text('25:00',0,0,74);text('把注意力，留给眼前这一段。',0,71,17,muted);arc(145,0,18,-Math.PI/2,Math.PI*1.1,green,4);break;
 case 'progress':
  text(item.label,-165,-25,21,ink,'left');text('50%',165,-25,18,muted,'right');rr(-165,13,330,8,4,'#dae6de');rr(-165,13,165,8,4,green);break;
 case 'slider':
  text(item.label,0,-42,18,muted);rr(-166,-2,332,7,4,'#dbe5df');const q=.7-.42*smooth((t-10.5)/.85);rr(-166,-2,332*q,7,4,green);arc(-166+332*q,1.5,11,0,Math.PI*2,'#fff',12);break;
 case 'toggle':
  text(item.label,-125,0,22,ink,'left');rr(63,-20,67,40,20,green);rr(94,-15,30,30,15,'#fff');break;
 case 'tabs':
  for(let j=0;j<3;j++){if(j===1)rr(-58,-23,116,46,23,ink);text(item.labels[j],(j-1)*120,0,21,j===1?'#fff':muted);}break;
 case 'chart':{
  text(item.label,-165,-97,20,muted,'left');text(item.values.reduce((a,b)=>a+b,0)+' 段',-165,-49,40,ink,'left');text('本周专注',167,-51,16,muted,'right');
  for(let j=0;j<4;j++)line(-165,7+j*24,165,7+j*24,'#ecf0ec',1);
  const vals=item.values,points=vals.map((v,j)=>[-165+j*55,78-v*17]);
  g.beginPath();g.moveTo(points[0][0],80);for(const p of points)g.lineTo(...p);g.lineTo(points.at(-1)[0],80);g.closePath();const grad=g.createLinearGradient(0,-20,0,80);grad.addColorStop(0,'#78c6a34d');grad.addColorStop(1,'#78c6a300');g.fillStyle=grad;g.fill();
  g.beginPath();points.forEach((p,j)=>j?g.lineTo(...p):g.moveTo(...p));g.lineWidth=3;g.strokeStyle='#55a882';g.stroke();for(const p of points)arc(...p,3,0,Math.PI*2,'#55a882',2);break;}
 case 'command':{
  text(item.label,-173,-75,19,muted,'left');line(-185,-40,185,-40,'#e2e9e3',1);const chars=Math.floor(smooth((t-18.35)/.85)*item.query.length);text(item.query.slice(0,chars),-170,9,25,ink,'left');
  if(t%1<.55){const measure=g.measureText(item.query.slice(0,chars)).width;line(-168+measure,-6,-168+measure,24,'#55a882',2);}rr(-176,58,352,43,9,'#edf5ee');text('↵  留下这一句',-155,80,17,muted,'left');break;}
 case 'toast':check(-140,0,.55);text(item.label,10,0,23,ink);break;
 }
 g.restore();
}
function body(k,t){const current=S.states[k],next=S.states[Math.min(k+1,S.states.length-1)];
 const p=smooth((t-current.start-1.45)/.55),a=current.shape,b=next.shape;
 const v=a.map((n,i)=>lerp(n,b[i],p));
 g.save();g.shadowColor='#1c3a2520';g.shadowBlur=lerp(18,26,v[1]/270);g.shadowOffsetY=12;
 const ca=current.dark?20:255,cb=next.dark?20:255,c=Math.round(lerp(ca,cb,p));
 rr(640-v[0]/2,365-v[1]/2,v[0],v[1],v[2],`rgb(${c},${c},${c})`);g.restore();
 contents(k,t,1-p);contents(Math.min(k+1,S.states.length-1),t,p);
}
function cursor(t){const k=Math.min(S.states.length-2,Math.floor(t/2)),s=S.states[k],next=S.states[k+1];
 const previous=S.states[Math.max(0,k-1)],p=smooth((t-s.start-.2)/.8);
 let x=lerp(previous.cursor[0],s.cursor[0],p),y=lerp(previous.cursor[1],s.cursor[1],p);
 if(s.kind==='slider'){const q=.7-.42*smooth((t-10.5)/.85);x=640-166+332*q;y=366;}
 const click=smooth((t-s.start-1.05)/.08)*(1-smooth((t-s.start-1.2)/.13));
 g.save();g.translate(x,y);g.scale(1-.15*click,1-.15*click);g.shadowColor='#0003';g.shadowBlur=4;g.shadowOffsetY=2;g.beginPath();g.moveTo(0,0);g.lineTo(0,25);g.lineTo(6,19);g.lineTo(11,31);g.lineTo(16,29);g.lineTo(11,17);g.lineTo(21,17);g.closePath();g.fillStyle=ink;g.fill();g.strokeStyle='#fff';g.lineWidth=1.6;g.stroke();g.restore();
 if(click>0)arc(x+3,y+4,12+10*(1-click),0,Math.PI*2,`rgba(83,164,123,${click*.5})`,2);
}
function render(t){t=Math.max(0,Math.min(S.duration-.0001,t));g.setTransform(1,0,0,1,0,0);g.globalAlpha=1;
 g.fillStyle='#eef1eb';g.fillRect(0,0,W,H);const gradient=g.createRadialGradient(640,330,60,640,360,740);gradient.addColorStop(0,'#fbfcf7');gradient.addColorStop(1,'#e4eae1');g.fillStyle=gradient;g.fillRect(0,0,W,H);
 text(S.brand,640,87,19,muted);text(S.title,640,130,30,ink);body(Math.min(S.states.length-2,Math.floor(t/2)),t);cursor(t);
 text('从一件事开始，把今天过轻一点。',640,624,18,muted);text('留 白  /  概 念 界 面',640,664,11,'#97a298');
}
window.render=render;window.DUR=S.duration;window.READY=true;
