const C=document.querySelector('canvas'),c=C.getContext('2d'),S=await(await fetch('story.json')).json(),W=1280,H=720;
const E=x=>(x=Math.max(0,Math.min(1,x)),x*x*(3-2*x)),L=(a,b,t)=>a+(b-a)*t;
const colors={melody:'#d79a35',bass:'#269baf',inner:'#c56b94'};
const dia=m=>Math.floor(m/12)*7+[0,0,1,1,2,3,3,4,4,5,5,6][m%12];
const sys=n=>Math.floor(n.bar/2),px=n=>180+(n.bar%2)*480+n.beat*111+16;
const py=n=>250+sys(n)*235+(n.voice==='melody'?48-(dia(n.midi)-dia(64))*6:154-(dia(n.midi)-dia(43))*6);
function text(s,x,y,size,color='#342f33',align='left'){c.fillStyle=color;c.font=`${size}px Studio`;c.textAlign=align;c.fillText(s,x,y)}
function line(x,y,a,b,w=1,col='#5c5357'){c.strokeStyle=col;c.lineWidth=w;c.beginPath();c.moveTo(x,y);c.lineTo(a,b);c.stroke()}
function ellipse(x,y,rx,ry,col){c.fillStyle=col;c.beginPath();c.ellipse(x,y,rx,ry,-.28,0,Math.PI*2);c.fill()}
function clef(x,y){c.strokeStyle='#554b52';c.lineWidth=3;c.beginPath();c.moveTo(x+8,y+70);c.bezierCurveTo(x-18,y+44,x-4,y+18,x+15,y+30);c.bezierCurveTo(x+43,y+50,x+2,y+71,x-3,y+45);c.bezierCurveTo(x-5,y+16,x+26,y+3,x+17,y-17);c.bezierCurveTo(x+2,y-34,x+1,y+17,x+10,y+67);c.bezierCurveTo(x+19,y+92,x-7,y+91,x-7,y+78);c.stroke()}
function note(n,t){let x=px(n),y=py(n),on=t>=n.at&&t<n.at+n.length,col=on?colors[n.voice]:'#554b52';
 const top=250+sys(n)*235+(n.voice==='melody'?0:106),bottom=top+48;
 for(let yy=bottom+12;yy<=y+2;yy+=12)line(x-13,yy,x+13,yy,1.1);
 for(let yy=top-12;yy>=y-2;yy-=12)line(x-13,yy,x+13,yy,1.1);
 if(n.length>=2.2){c.strokeStyle=col;c.lineWidth=2;c.beginPath();c.ellipse(x,y,9,5,-.28,0,Math.PI*2);c.stroke()}
 else {ellipse(x,y,8,5,col);let down=y<top+24;line(x+(down?-7:7),y,x+(down?-7:7),y+(down?34:-34),1.6,col);if(n.length<.4){c.beginPath();c.moveTo(x+7,y-34);c.quadraticCurveTo(x+24,y-23,x+12,y-12);c.stroke()}}
 if(on){c.save();c.shadowBlur=26;c.shadowColor=col;ellipse(x,y,6,4,'#fff9e9');c.restore()}
}
function page(t){c.fillStyle='#f8f3e9';c.fillRect(0,0,1280,1770);for(let i=0;i<1100;i++){let x=(i*109.31)%1280,y=(i*197.77)%1770;c.fillStyle='rgba(100,83,70,.035)';c.fillRect(x,y,1,2)}
 text(S.title,640,105,34,'#443b40','center');text('P I A N O     /     轻柔地',640,145,15,'#85797a','center');
 const marks=[['旋律',colors.melody],['低音',colors.bass]];marks.forEach(([s,col],i)=>{ellipse(492+i*145,184,4,4,col);text(s,505+i*145,189,13,col)});
 for(let k=0;k<6;k++){let y=250+k*235;for(let st=0;st<2;st++)for(let l=0;l<5;l++)line(110,y+st*106+l*12,1170,y+st*106+l*12,.8,'#a19696');
  line(110,y,110,y+154,2);line(655,y,655,y+154,1);line(1170,y,1170,y+154,1.5);clef(125,y);
  text('4',166,y+20,18);text('4',166,y+42,18);text('4',166,y+126,18);text('4',166,y+148,18);
  c.beginPath();c.strokeStyle='#554b52';c.lineWidth=2.5;c.arc(137,y+123,13,-2.6,1.5);c.stroke();ellipse(134,y+116,5,5,'#554b52');ellipse(155,y+116,2,2,'#554b52');ellipse(155,y+130,2,2,'#554b52');
  text(String(k*2+1),115,y-20,12,'#a19696');
 }
 for(const n of S.notes)note(n,t);
 for(const voice of ['melody','bass']){let ns=S.notes.filter(n=>n.voice===voice),idx=ns.findLastIndex(n=>n.at<=t),n=ns[Math.max(0,idx)];if(idx<0||t>n.at+n.length+.1)continue;let prev=ns[Math.max(0,idx-1)],q=E((t-n.at+.12)/.20);let same=sys(prev)===sys(n),x=same?L(px(prev),px(n),q):px(n),y=same?L(py(prev),py(n),q)-Math.sin(q*Math.PI)*35:py(n);
 c.save();c.shadowColor=colors[voice];c.shadowBlur=22;ellipse(x,y,6,6,'#fff7d7');c.shadowBlur=0;c.strokeStyle=colors[voice];c.lineWidth=2;c.beginPath();c.arc(x,y,10,0,Math.PI*2);c.stroke();c.restore()}
}
await document.fonts.load('24px Studio');window.DUR=S.duration;window.render=t=>{c.setTransform(1,0,0,1,0,0);let g=c.createRadialGradient(640,300,30,640,360,900);g.addColorStop(0,'#67616d');g.addColorStop(1,'#24242f');c.fillStyle=g;c.fillRect(0,0,W,H);
 let beat=Math.max(0,(t-1.2)/.6),system=Math.min(5,Math.floor(beat/8)),p=beat%8,view=system+(system<5?E((p-6.4)/1.6):0),intro=E(t/2.2),out=E((t-29.3)/2.8),zoom=L(.70,1.02,intro)*(1-out*.19),cy=L(580,340+view*235,intro);cy=L(cy,1480,out);
 c.translate(640,360);c.rotate(-.055);c.scale(zoom,zoom);c.translate(-640,-cy);c.shadowColor='#0009';c.shadowBlur=34;c.fillStyle='#f8f3e9';c.fillRect(0,0,1280,1770);c.shadowBlur=0;page(t);c.setTransform(1,0,0,1,0,0);if(t>30.2){c.globalAlpha=E((t-30.2)/1);text('把最后一个音，留给窗外的风。',640,675,20,'#f8f1e2','center');c.globalAlpha=1}};window.READY=true;window.render(0);
