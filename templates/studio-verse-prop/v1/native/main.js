const S=await fetch('story.json').then(r=>r.json());
await document.fonts.load('48px Studio');
const c=document.querySelector('canvas'),g=c.getContext('2d'),W=720,H=1280;
const cap=x=>Math.max(0,Math.min(1,x)),E=x=>{x=cap(x);return x*x*(3-2*x)},P=(t,a,b)=>E((t-a)/(b-a));
const mix=(a,b,t)=>a+(b-a)*t;
function text(s,x,y,size=32,color='#36352f'){g.fillStyle=color;g.font=`${size}px Studio`;g.textAlign='center';g.textBaseline='middle';g.fillText(s,x,y);}
function line(x,y,X,Y,color,w=2){g.strokeStyle=color;g.lineWidth=w;g.lineCap='round';g.beginPath();g.moveTo(x,y);g.lineTo(X,Y);g.stroke();}
function disc(x,y,r,color){g.fillStyle=color;g.beginPath();g.arc(x,y,r,0,7);g.fill();}
function bg(t){g.fillStyle='#e9e0cf';g.fillRect(0,0,W,H);const light=g.createRadialGradient(260,400,60,360,640,800);light.addColorStop(0,'#fffaf0');light.addColorStop(1,'#c9b99e');g.fillStyle=light;g.fillRect(0,0,W,H);g.fillStyle='#796b4b0b';for(let i=0;i<2300;i++){const x=(i*331)%W,y=(i*173)%H;g.fillRect(x,y,1+(i%3),1);}g.fillStyle='#6b5c4318';for(let i=0;i<7;i++){g.save();g.translate(730,150+i*42);g.rotate(-.48);g.fillRect(-70,0,440,14);g.restore();}}
function envelope(t){
 const q=P(t,1,4),fold=P(t,4,5.5);g.save();g.translate(360,600);g.rotate(-.055);
 g.shadowColor='#43372338';g.shadowBlur=25;g.shadowOffsetY=18;
 const gradient=g.createLinearGradient(-250,-210,250,210);gradient.addColorStop(0,'#fdf3df');gradient.addColorStop(1,'#ccb995');
 g.fillStyle=gradient;g.fillRect(-250,-190,500,340);g.shadowBlur=0;g.shadowOffsetY=0;
 line(-250,-190,0,40,'#b7a581',2);line(250,-190,0,40,'#b7a581',2);
 g.save();g.translate(0,-170+q*160);g.rotate(.04*(1-q));g.fillStyle='#fff9e8';g.fillRect(-190,-195,380,250*(1-.5*q));
 text('致  远 方',0,-130,30);for(let j=0;j<4;j++)line(-140,-75+j*26,100-j*15,-75+j*26,'#74705a66',2);g.restore();
 g.fillStyle='#ede1c7';g.beginPath();g.moveTo(-250,150);g.lineTo(0,-20);g.lineTo(250,150);g.closePath();g.fill();
 const h=mix(-175,120,fold);g.fillStyle='#f0e4c9';g.beginPath();g.moveTo(-250,-190);g.lineTo(250,-190);g.lineTo(0,h);g.closePath();g.fill();line(-250,-190,250,-190,'#bca988');
 g.globalAlpha=fold;disc(0,105,27,'#a13535');text('念',0,106,24,'#f7ddbb');g.globalAlpha=1;g.restore();
}
function fan(t){const q=P(t,6.3,8.7)*(1-.82*P(t,10.2,11.8)),angle=.15+q*1.9;
 g.save();g.translate(360,820);g.rotate(-.1);g.shadowColor='#45382744';g.shadowBlur=30;g.shadowOffsetY=15;
 const paper=g.createLinearGradient(0,-510,0,-90);paper.addColorStop(0,'#fff7df');paper.addColorStop(1,'#c9b080');g.fillStyle=paper;
 g.beginPath();g.arc(0,0,500,-Math.PI/2-angle/2,-Math.PI/2+angle/2);g.arc(0,0,85,-Math.PI/2+angle/2,-Math.PI/2-angle/2,true);g.closePath();g.fill();g.shadowBlur=0;g.shadowOffsetY=0;
 for(let j=0;j<19;j++){const a=-Math.PI/2-angle/2+j*angle/18;line(Math.cos(a)*25,Math.sin(a)*25,Math.cos(a)*500,Math.sin(a)*500,j%2?'#8d68414d':'#fff6dc',j%2?3:2);}
 for(let j=0;j<12;j++){const a=-Math.PI/2-angle*.42+j*angle*.072,rad=260+(j%3)*36;disc(Math.cos(a)*rad,Math.sin(a)*rad,4+j%3,'#8e262c');}
 line(0,0,Math.cos(-Math.PI/2-angle/2)*510,Math.sin(-Math.PI/2-angle/2)*510,'#785137',10);line(0,0,Math.cos(-Math.PI/2+angle/2)*510,Math.sin(-Math.PI/2+angle/2)*510,'#785137',10);disc(0,0,10,'#aa8455');
 g.globalAlpha=q;text('见字如晤',0,-230,35,'#655d48');g.globalAlpha=1;g.restore();
}
function ribbon(t,asWipe=false){g.save();g.strokeStyle='#a33038';g.lineWidth=asWipe?190:50;g.lineCap='round';
 const move=asWipe?P(t,11.3,12.6):P(t,12,16);
 g.beginPath();for(let j=0;j<160;j++){const p=j/159,x=-140+p*1000,y=asWipe?mix(-250,1480,move)+Math.sin(p*6+t)*130:610+Math.sin(p*7-t*.7)*145; j?g.lineTo(x,y):g.moveTo(x,y);}g.shadowColor='#65252d44';g.shadowBlur=18;g.shadowOffsetY=16;g.stroke();
 g.shadowBlur=0;g.shadowOffsetY=0;g.strokeStyle='#e7818177';g.lineWidth=asWipe?7:4;g.stroke();g.restore();}
function blossom(t){const grow=P(t,18,22);g.save();g.translate(100,900);g.scale(.45+grow*.55,.45+grow*.55);line(-60,130,470,-450,'#393b33',15);line(100,-40,110,-330,'#393b33',9);line(260,-230,500,-210,'#393b33',8);line(350,-320,370,-530,'#393b33',6);for(let i=0;i<26;i++){const p=i/25,x=-15+p*440,y=110-p*560+Math.sin(i*4)*80;if(p>grow+.08)continue;g.save();g.translate(x,y);g.rotate(i*1.2);for(let j=0;j<5;j++){g.save();g.rotate(j*1.256);g.fillStyle=['#c36575','#e0a1a2','#9e3e50'][i%3];g.beginPath();g.ellipse(0,-12,10,17,0,0,7);g.fill();g.restore();}disc(0,0,4,'#d6b96c');g.restore();}g.restore();}
function render(t){t=Math.min(S.duration-.001,Math.max(0,t));g.setTransform(1,0,0,1,0,0);g.globalAlpha=1;bg(t);
 const section=Math.min(3,Math.floor(t/6));if(section===0)envelope(t);if(section===1)fan(t);if(section===2)ribbon(t);if(section===3)blossom(t);
 if(t>5.45&&t<6.4){const p=P(t,5.45,6.4);g.save();g.translate(mix(-1000,1000,p),0);g.rotate(-.15);g.fillStyle='#e8d6ad';g.fillRect(-530,-200,1060,1700);for(let j=0;j<9;j++)line(-500+j*125,-200,-500+j*125,1700,'#beaa82',2);g.restore();}
 if(t>11.3&&t<12.6)ribbon(t,true);
 if(t>17.45&&t<18.65){const p=P(t,17.45,18.65);for(let i=0;i<12;i++)disc(360+Math.cos(i)*170,640+Math.sin(i*2)*300,p<.7?p*1700:(1-p)*4000,'#222c29');}
 const local=t-section*6;g.globalAlpha=Math.min(P(local,.3,.9),1-P(local,5.6,6));text(S.scenes[section].text,360,1085,31);g.globalAlpha=1;
 text(S.title,360,145,27,'#5d5544');text('原 创 诗 句  /  纸 上 寄 意',360,192,13,'#8b7b61');
 line(110,1160,610,1160,'#a99a7e66',1);line(110,1160,110+500*t/S.duration,1160,'#a13535',2);
 if(t>22){g.globalAlpha=P(t,22,23);text('见字，如见你。',360,305,41,'#8f3440');g.globalAlpha=1;}
}
window.DUR=S.duration;window.render=render;window.READY=true;
