const story=await(await fetch('story.json')).json();
await document.fonts.load('500 28px Studio');
const c=document.querySelector('canvas'),x=c.getContext('2d');
const W=720,H=1280,cl=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=v=>{v=cl(v);return v*v*(3-2*v)};
function text(s,px,py,size=28,color='#253c39',align='left',weight=500){x.fillStyle=color;x.font=`${weight} ${size}px Studio`;x.textAlign=align;x.fillText(s,px,py)}
function line(points,color,width=2){x.strokeStyle=color;x.lineWidth=width;x.beginPath();points.forEach((p,i)=>i?x.lineTo(...p):x.moveTo(...p));x.stroke()}
function rr(a,b,w,h,r,color){x.fillStyle=color;x.beginPath();x.roundRect(a,b,w,h,r);x.fill()}
function lemon(px,py,r,rot=0){x.save();x.translate(px,py);x.rotate(rot);x.fillStyle='#e2b23c';x.beginPath();x.arc(0,0,r,0,Math.PI*2);x.fill();x.fillStyle='#fff5bd';x.beginPath();x.arc(0,0,r-5,0,Math.PI*2);x.fill();for(let i=0;i<8;i++){let a=i*Math.PI/4+.05;x.fillStyle='#f1d65b';x.beginPath();x.moveTo(0,0);x.arc(0,0,r-9,a,a+Math.PI/4-.1);x.closePath();x.fill()}x.restore()}
function glassPath(){x.beginPath();x.moveTo(205,475);x.lineTo(205,944);x.quadraticCurveTo(205,964,225,966);x.lineTo(495,966);x.quadraticCurveTo(515,964,515,944);x.lineTo(515,475);x.closePath()}
function ice(px,py,rot,alpha=1){x.save();x.translate(px,py);x.rotate(rot);x.globalAlpha=alpha;rr(-35,-35,70,70,13,'#e7f0e8a8');x.strokeStyle='#8aaea470';x.lineWidth=2;x.stroke();line([[-20,-23],[17,-23],[25,-15]],'#ffffffd0',4);x.restore()}
window.render=t=>{
 t=cl(t,0,30);x.clearRect(0,0,W,H);x.fillStyle='#f2eee4';x.fillRect(0,0,W,H);
 const bg=x.createLinearGradient(0,350,720,1050);bg.addColorStop(0,'#e8e9db');bg.addColorStop(1,'#f2eee4');x.fillStyle=bg;x.fillRect(0,352,720,670);
 text('一杯，慢下来。',56,132,49,'#253c39','left',600);text('柠檬气泡茶 / 30秒自制配方',58,183,23,'#74827a');
 line([[58,223],[662,223]],'#b7c0b2',1);
 let step=story.steps.findLast(s=>t>=s.start)||story.steps[0];
 text(String(story.steps.indexOf(step)+1).padStart(2,'0'),58,303,43,'#a3aa91');
 text(step.title,134,289,30);text(step.caption,134,330,21,'#74827a');
 x.fillStyle='#9aa58f28';x.beginPath();x.ellipse(361,984,172,24,0,0,Math.PI*2);x.fill();
 const total=story.steps.reduce((n,s)=>n+(s.ml||0)*ease((t-s.start-.5)/2.3),0);
 const level=944-total*1.8;
 // A single calibrated glass persists throughout; all pours accumulate.
 x.save();glassPath();x.clip();
 let grad=x.createLinearGradient(0,level,0,970);grad.addColorStop(0,total>170?'#d8bb54cc':'#b98544c4');grad.addColorStop(1,'#b98339d9');x.fillStyle=grad;
 if(total>.01){x.beginPath();x.moveTo(180,944);x.lineTo(180,level);for(let a=180;a<=540;a+=5)x.lineTo(a,level+Math.sin(a*.035+t*5)*Math.exp(-Math.max(0,t-step.start-2.5))*4);x.lineTo(540,944);x.closePath();x.fill();}
 let iceIn=ease((t-1.3)/1.5);[[-58,0,-.12],[26,-32,.2],[-3,61,.1],[49,72,-.17]].forEach(([a,b,r],i)=>ice(359+a,Math.min(880+b,Math.max(level+50+b,560+b))+(1-iceIn)*-500,r,iceIn));
 if(total>110)for(let i=0;i<24;i++){let py=944-((t*25+i*41)%Math.max(1,944-level));let px=245+((i*73)%228);x.strokeStyle='#fff6c46a';x.lineWidth=1;x.beginPath();x.arc(px,py,1.6+i%3,0,Math.PI*2);x.stroke()}
 x.restore();
 x.strokeStyle='#53766e';x.lineWidth=3;glassPath();x.stroke();
 line([[217,490],[217,916]],'#ffffffb0',6);line([[503,490],[503,916]],'#ffffffa0',3);
 x.strokeStyle='#53766e';x.lineWidth=2;x.beginPath();x.ellipse(360,475,155,13,0,0,Math.PI*2);x.stroke();
 for(let ml=50;ml<=200;ml+=50){let yy=944-ml*1.8;line([[478,yy],[490,yy]],'#6c776c99',1);text(ml+'',500,yy+6,16,'#74827a')}
 // Only one measured ingredient is in motion at once.
 const active=story.steps.find(s=>s.ml&&t>s.start+.5&&t<s.start+2.8);
 if(active){let f=ease((t-active.start-.5)/2.3),flow=Math.sin(Math.PI*f);x.save();x.strokeStyle=active.color;x.lineWidth=10*flow+2;x.lineCap='round';x.beginPath();x.moveTo(414,392);x.bezierCurveTo(408,425,392,451,390,Math.max(482,level));x.stroke();x.restore();x.save();x.translate(414,392);x.rotate(-.7);rr(-10,-73,20,75,6,active.color);rr(-26,-138,52,90,11,active.color);rr(-19,-116,38,37,3,'#f2eee4');x.restore();}
 if(t>21.8){let f=ease((t-21.8)/1);lemon(485,488-(1-f)*145,48,.1);}
 if(t>23.5){let f=ease((t-23.5)/1);x.save();x.translate(432,485-(1-f)*110);x.rotate(-.5);x.fillStyle='#5f8050';for(let i=0;i<3;i++){x.save();x.rotate(i*.85);x.beginPath();x.ellipse(0,-16,10,26,.2,0,Math.PI*2);x.fill();x.restore()}x.restore()}
 if(t>24&&t<26.5){x.save();x.translate(360+Math.sin(t*6)*12,450);x.rotate(Math.sin(t*6)*.08);rr(-3,-74,6,415,3,'#a88d5c');x.restore()}
 text(Math.round(total)+' mL',360,1056,37,'#253c39','center',600);
 text(t<26?'不含冰块、柠檬片与薄荷的体积':'80 + 80 + 20 + 10 = 190 mL',360,1096,20,'#74827a','center');
 let labels=story.steps.filter(s=>s.ml);labels.forEach((s,i)=>{let done=t>s.start+.5;rr(58+i*153,1151,140,47,23,done?'#dce2d0':'#e6e5db');text(s.short,128+i*153,1181,19,done?'#253c39':'#91998b','center')});
 const progress=cl(t/30);rr(58,1235,604,3,1,'#d7d9cd');rr(58,1235,604*progress,3,1,'#75876b');
};window.render(0);window.DUR=story.duration;window.READY=true;
