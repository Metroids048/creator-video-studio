import {ctx,S,bg,text,line,circle,poly,phase,lerp,rng,grain,ready} from './draw.js';
// Song words drive the pictured objects and camera. No narration or score UI.
const paper='#f0e9d7', ink='#344c49';
const transitionCanvas=document.createElement('canvas');transitionCanvas.width=1280;transitionCanvas.height=720;const transitionContext=transitionCanvas.getContext('2d');
function wash(x,y,rx,ry,c,seed=1,alpha=.10){
 const r=rng(seed);ctx.save();ctx.fillStyle=c;
 const inheritedAlpha=ctx.globalAlpha;for(let n=0;n<8;n++){ctx.globalAlpha=inheritedAlpha*alpha;ctx.beginPath();for(let i=0;i<40;i++){let a=i*Math.PI/20,k=.89+r()*.19;let px=x+Math.cos(a)*rx*k,py=y+Math.sin(a)*ry*k;i?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath();ctx.fill()}ctx.restore();
}
function brush(pts,c,width=2){ctx.save();ctx.lineCap='round';ctx.lineJoin='round';ctx.strokeStyle=c;ctx.lineWidth=width;ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.stroke();ctx.restore()}
function ridge(y,height,c,seed){const r=rng(seed),pts=[[-100,650],[-100,y]];for(let x=-80;x<=1380;x+=45)pts.push([x,y-Math.sin(x/180+seed)*height*(.7+r()*.3)-r()*height*.23]);pts.push([1380,650]);ctx.save();ctx.globalAlpha=.6;poly(pts,c);ctx.translate(0,5);ctx.globalAlpha=.08;poly(pts,c);ctx.restore()}
function sky(night=false,sunset=false){bg(paper);wash(650,225,840,400,night?'#8595a5':sunset?'#d9b486':'#bbc8bc',20,.045);wash(350,80,420,120,night?'#61798a':'#d7d2ae',7,.055);if(sunset){wash(935,270,155,125,'#e0a15e',81,.06);circle(935,270,39,'#da9c67')}if(night){wash(950,170,100,85,'#d9dcba',83,.035);circle(950,170,37,'#e8e4c8')}ridge(415,87,night?'#697f87':'#adb9ac',1);ridge(465,104,night?'#556e77':'#91a99d',8);wash(650,470,850,83,night?'#c1c8bc':'#e0dfc5',10,.06)}
function water(t,night=false){wash(680,555,880,130,night?'#8daba8':'#a9beb1',16,.055);for(let i=0;i<38;i++){let x=(i*173)%1350,y=480+(i*43)%156;let len=23+(i*19)%103;line(x+Math.sin(t*.4+i)*9,y,x+len+Math.sin(t*.4+i)*9,y,night?'#a9c1b9':'#d0d3b8',.5+(i%3)*.5)}}
function bank(y=510){poly([[-100,y+20],[90,y-35],[260,y-10],[390,y-35],[570,y-15],[715,y+25],[1380,670],[-100,720]],'#a9b89a');wash(260,y+22,520,100,'#9ba982',92,.07);wash(200,y+70,300,60,'#bbb995',33,.05)}
function grass(t,x0=0,y0=610,span=1280,amount=210){let r=rng(12);for(let i=0;i<amount;i++){let x=x0+r()*span,y=y0+r()*65,h=9+r()*42,sw=Math.sin(t*.9+i*.7)*5;brush([[x,y],[x+sw*.6,y-h*.6],[x+sw,y-h]],i%4?'#7f9274':'#a6a478',.7+r())}}
function pavilion(x,y,s=1){ctx.save();ctx.translate(x,y);ctx.scale(s,s);wash(0,7,150,28,'#788c7d',47,.06);poly([[-123,-154],[-71,-176],[0,-212],[73,-175],[123,-154],[93,-144],[-94,-144]],'#53685e');brush([[-126,-153],[-85,-153],[0,-172],[85,-153],[126,-153]],'#d1c9a6',2);for(let i of[-78,-58,58,78])line(i,-144,i,-8,'#6c7160',8);for(let i of[-76,-55,55,76])line(i-2,-140,i-2,-10,'#b1aa85',2);line(-85,-57,85,-57,'#777f66',5);line(-95,-9,95,-9,'#6a7565',9);poly([[-111,-1],[107,-1],[129,19],[-134,19]],'#b1af8d');poly([[-134,19],[129,19],[150,33],[-157,33]],'#c1bd9d');for(let i=0;i<8;i++)line(-78+i*23,-176+Math.abs(i-3.5)*5,-95+i*27,-153,'#809084',1);ctx.restore()}
function road(){poly([[368,458],[384,461],[675,630],[930,720],[515,720],[507,619]],'#c7bea0');brush([[377,460],[467,540],[555,600],[735,693]],'#e2d7b7',3)}
function person(x,y,s=1,coat='#687d72',walk=0){ctx.save();ctx.translate(x,y);ctx.scale(s,s);line(-4,0,-5+Math.sin(walk)*6,22,ink,3);line(4,0,5-Math.sin(walk)*6,22,ink,3);wash(0,-19,14,24,coat,4,.15);wash(0,-50,9,10,'#c3aa88',5,.17);wash(-1,-58,10,5,'#44594e',6,.2);line(-10,-27,-16,-12,'#8e967b',3);line(9,-26,15,-14,'#8e967b',3);ctx.restore()}
function willow(t,x=1150,y=50,s=1){ctx.save();ctx.translate(x,y);ctx.scale(s,s);brush([[155,620],[70,397],[20,190],[-40,80],[-173,13]],'#66735d',23);brush([[80,400],[85,230],[25,75],[-29,-10]],'#6b775d',14);for(let j=0;j<27;j++){let sx=-150+j*14,sy=10+Math.sin(j*.5)*30,len=210+(j*31)%220;const sway=Math.sin(t*.6+j*.19)*17;brush([[sx,sy],[sx-24+sway,sy+len*.5],[sx-18+sway*1.3,sy+len]],'#829371',1.1);for(let k=0;k<13;k++){let yy=sy+len*k/13,xx=sx-16+sway*k/13;ctx.save();ctx.translate(xx,yy);ctx.rotate(-.5+Math.sin(t*.6+j)*.08);ctx.fillStyle=k%3?'#91a27b':'#b0b18b';ctx.beginPath();ctx.ellipse(0,0,3,10,0,0,Math.PI*2);ctx.fill();ctx.restore()}}ctx.restore()}
function birds(t,x,y,n=3){for(let i=0;i<n;i++){let xx=x+i*30+t*7,yy=y+Math.sin(t*.6+i)*10;brush([[xx-6,yy-2],[xx,yy+Math.sin(t*4+i)*3],[xx+7,yy-3]],'#68786c',1.3)}}
function boat(x,y,s=1){ctx.save();ctx.translate(x,y);ctx.scale(s,s);poly([[-68,0],[72,0],[47,17],[-44,17]],'#586e64');brush([[-67,0],[0,4],[72,0]],'#c6bd95',2);person(3,-11,.66);line(10,-52,55,22,'#606e58',2);ctx.restore()}
function cup(x,y,s=1){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.fillStyle='#cfc9a9';ctx.beginPath();ctx.ellipse(0,0,45,16,0,0,Math.PI*2);ctx.fill();poly([[-44,0],[-28,53],[28,53],[44,0]],'#b2b399');ctx.fillStyle='#ded6b2';ctx.beginPath();ctx.ellipse(0,1,41,12,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#7b8569';ctx.beginPath();ctx.ellipse(0,3,34,8,0,0,Math.PI*2);ctx.fill();brush([[-25,13],[-15,40],[12,43]],'#e3dfc6',2);ctx.restore()}
function scene(i,t){
 if(i===0){sky();water(t);bank(554);road();pavilion(295,478,.9);grass(t,0,625,1280,135);grass(t,0,545,350,45);person(760-t*3,606,1.1,'#798e79',t*1.6);person(345,481,.65,'#aa8469');willow(t,1260,10,.7);birds(t,630,250,4);}
 if(i===1){sky();water(t);bank(568);poly([[478,548],[506,554],[1060,720],[667,720]],'#c7bea0');brush([[494,552],[668,616],[900,700]],'#e2d7b7',3);pavilion(385,548,1.44);person(428,549,1.03,'#aa8469');person(875-(t-7)*19,619,1.38,'#798e79',t*1.6);grass(t,0,641,1280,230);willow(t,1350,-55,.95);birds(t,620,220,3);}
 if(i===2){
  bg(paper);wash(640,90,950,230,'#c4d0bf',23,.065);ridge(240,45,'#b6c2ac',14);ridge(280,36,'#a0b49a',17);
  wash(640,490,1000,300,'#a7b58b',32,.09);wash(230,590,550,180,'#879d77',43,.07);
  const r=rng(72);for(let j=0;j<220;j++){let z=r(),x=r()*1350-35,y=310+z*390,h=25+z*z*225,sw=Math.sin(t*1.1-x*.008)*(.5+z)*24;
   ctx.save();ctx.strokeStyle=j%4?'#708c66':'#a2a56c';ctx.lineWidth=1+z*3;ctx.beginPath();ctx.moveTo(x,y);ctx.bezierCurveTo(x-6,y-h*.25,x+sw,y-h*.7,x+sw,y-h);ctx.stroke();
   if(j%5===0){for(let k=0;k<5;k++){wash(x+sw+(k%2?5:-5),y-h+k*7,3+z*2,5,'#b6ad78',j+k,.1)}}ctx.restore()}
  birds(t,620,170,3);
 }

 if(i===3){
  bg(paper);wash(640,340,1000,500,'#b8c6b4',31,.07);water(t);wash(750,650,750,180,'#869f97',61,.08);
  brush([[-60,80],[220,55],[480,95],[740,70],[990,-25]],'#62745d',19);
  for(let j=0;j<23;j++){let x=50+j*49,yy=70+Math.sin(j*.6)*24,len=245+(j*47)%270,sw=Math.sin(t*.7+j*.31)*28;
   ctx.save();ctx.strokeStyle='#7d956f';ctx.lineWidth=1.7;ctx.beginPath();ctx.moveTo(x,yy);ctx.quadraticCurveTo(x-40+sw,yy+len*.5,x+sw,yy+len);ctx.stroke();
   for(let k=0;k<15;k++){let f=k/15;ctx.save();ctx.translate(x-15*Math.sin(f*Math.PI)+sw*f,yy+len*f);ctx.rotate(-.6+Math.sin(t*.7+j)*.13);ctx.fillStyle=k%4?'#8ba479':'#b6b88b';ctx.beginPath();ctx.ellipse(k%2?5:-5,0,4.5,16,0,0,Math.PI*2);ctx.fill();ctx.restore()}ctx.restore()}
  let p=phase(t,19,24.8),lx=710-145*p,ly=405+135*p;wash(lx,ly,11,4,'#a2ac75',24,.13);
  for(let j=0;j<3;j++){ctx.save();ctx.strokeStyle='#a5b9a8';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(570,555,20+30*p+j*28,3+5*p+j*3,0,0,Math.PI*2);ctx.stroke();ctx.restore()}
 }

 if(i===4){sky(false,true);water(t);ridge(489,135,'#748c83',15);ridge(545,94,'#5e7c72',28);wash(935,499,38,34,'#dca366',92,.06);for(let j=0;j<17;j++)line(885+j*5,535+j*4,965-j*3,535+j*4,'#c9b291',1);boat(280+(t-24.9)*5,560,.8);willow(t,1410,-10,.8);birds(t,660,278,2);}
 if(i===5){sky();water(t);ridge(493,155,'#708e7d',9);wash(270,490,460,70,'#d3d6bd',60,.09);boat(620+(t-31)*12,552,1);birds(t,430,280,3);grass(t,0,665,1280,70);}
 if(i===6){
  sky(false,true);water(t);wash(640,575,900,150,'#a9aa8b',21,.07);
  poly([[-20,50],[1000,50],[1250,0],[-20,0]],'#687761');line(100,35,100,610,'#7b8065',30);line(112,45,112,610,'#b4af8a',5);
  poly([[80,550],[1120,550],[1350,720],[-50,720]],'#b2b095');brush([[80,550],[1120,550]],'#8c947b',2);for(let k=0;k<7;k++)line(120+k*150,553,-20+k*205,720,'#a3a88d',1);
  const fade=phase(t,38.2,42.3);ctx.save();ctx.translate(-fade*12,0);ctx.globalAlpha=1-fade;person(360,548,2,'#aa8469');person(610,548,2,'#7d8f83');ctx.restore();person(850,548,2.05,'#6d8778');
  for(let j=0;j<8;j++){let p=phase(t,37.5+j*.18,42.5);wash(355+j*35-95*p,470+140*p,9,3,'#af966e',j,.12)}
 }

 if(i===7){sky(false,true);water(t);wash(640,613,515,70,'#827c60',70,.06);poly([[175,500],[1105,500],[1250,720],[20,720]],'#aca58b');for(let j=0;j<17;j++)brush([[175+j*55,500],[20+j*73,720]],'#8f937c',.6);let q=phase(t,42.7,44.7),lift=22*Math.sin(phase(t,42.7,46.7)*Math.PI),lx=480+q*77,rx=800-q*77;poly([[0,672],[0,593],[lx-90,550-lift],[lx-65,590-lift]],'#71867b');poly([[1280,672],[1280,593],[rx+90,550-lift],[rx+65,590-lift]],'#a18e70');wash(lx-62,554-lift,42,19,'#c8b28d',19,.14);wash(rx+62,554-lift,42,19,'#c8b28d',19,.14);cup(lx,520-lift,1.8);cup(rx,520-lift,1.8);birds(t,400,260,2);}
 if(i>=8){sky(true);water(t,true);bank(586);pavilion(345,502,.95);person(360,503,.72,'#6b8076');boat(910+(t-49)*8,549,.54);willow(t,1340,20,.9);grass(t,0,650,1280,140);for(let j=0;j<11;j++)line(914-j*3,520+j*9,975+j*4,520+j*9,'#cfceb0',1);}
}
ready(t=>{
 let i=Math.max(0,S.scenes.findLastIndex(s=>t>=s.start)),cur=S.scenes[i];
 const local=phase(t,cur.start,cur.end),zoom=1+.024*local;
 ctx.save();ctx.translate(640,365);ctx.scale(zoom,zoom);ctx.translate(-640+Math.sin(t*.08)*3,-365);scene(i,t);ctx.restore();
 // A brief paper dissolve connects locations without introducing title cards.
 let dissolve=1-phase(t,cur.start,cur.start+.8);if(i>0&&dissolve>0){transitionContext.clearRect(0,0,1280,720);transitionContext.drawImage(ctx.canvas,0,0);ctx.save();scene(i-1,cur.start-.01);ctx.globalAlpha=1-dissolve;ctx.drawImage(transitionCanvas,0,0);ctx.restore()}
 grain(23,.055);
 const shade=ctx.createLinearGradient(0,590,0,720);shade.addColorStop(0,'rgba(240,233,215,0)');shade.addColorStop(1,'rgba(240,233,215,.94)');ctx.fillStyle=shade;ctx.fillRect(0,590,1280,130);
 if(i===0){ctx.save();ctx.globalAlpha=(1-phase(t,3.2,6));text('送 别',640,245,58,ink,'center',500);text('长亭外，一程山水。',640,300,19,'#697969','center');ctx.restore()}
 if(cur.lyric){ctx.save();ctx.globalAlpha=phase(t,cur.start+.15,cur.start+.7)*(1-phase(t,cur.end-.55,cur.end));text(cur.lyric,640,657,27,'#3e574e','center');ctx.restore()}
 ctx.save();ctx.globalAlpha=phase(t,53.6,55);ctx.fillStyle=paper;ctx.fillRect(0,0,1280,720);text('山水有相逢',640,360,27,'#677c70','center');ctx.restore();
});
