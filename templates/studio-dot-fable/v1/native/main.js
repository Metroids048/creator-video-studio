import{ctx,S,bg,text,line,circle,poly,ease,phase,lerp,eyes,ready}from'./draw.js';
// One character keeps its identity, crosses three obstacles and creates the ending.
function ball(x,y,r,t,mood=0){ctx.save();ctx.translate(x,y);let q=1+.08*Math.sin(t*9);ctx.scale(q,1/q);circle(0,0,r,'#ed492d');circle(-r*.25,-r*.3,r*.27,'#ff6d43');eyes(0,-4,r/38);ctx.strokeStyle='#451e22';ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(0,5,r*.31,mood?0:Math.PI, mood?Math.PI:2*Math.PI);ctx.stroke();ctx.restore()}
function star(x,y,r,col){poly(Array.from({length:10},(_,i)=>{let a=-Math.PI/2+i*Math.PI/5;return[x+Math.cos(a)*r*(i%2?.4:1),y+Math.sin(a)*r*(i%2?.4:1)]}),col)}
ready(t=>{const night=phase(t,8,11);bg(`rgb(${Math.round(245-225*night)},${Math.round(240-215*night)},${Math.round(224-186*night)})`);
 let ground='#9eaa7b';poly([[0,510],[180,475],[400,505],[660,470],[900,493],[1280,450],[1280,720],[0,720]],ground);poly([[0,560],[300,535],[600,575],[980,510],[1280,530],[1280,720],[0,720]],'#6c8566');
 for(let i=0;i<9;i++){let x=i*170-30;line(x,520,x,495,'#456341',2);circle(x,493,6,'#f1d16e')}
 const q=phase(t,0,3);let x=lerp(145,455,q),y=482-135*Math.sin(q*Math.PI);let titleColor=night>.5?'#f3ecd9':'#202e29';
 if(t>=3&&t<7){const p=phase(t,3,7);x=lerp(455,790,p);y=480-185*Math.sin(p*Math.PI);poly([[570,510],[570,415],[635,415],[635,510]],'#a48160');poly([[635,510],[635,445],[670,445],[670,510]],'#c5a079')}
 if(t>=7&&t<11){let p=phase(t,7,11);x=lerp(790,1040,p);y=480-270*Math.sin(p*Math.PI/2)}
 if(t>=11){let p=phase(t,11,15);x=lerp(1040,640,p);y=lerp(210,350,p);for(let i=0;i<34;i++){let a=i*2.399,rr=100+(i%6)*44;star(640+Math.cos(a+t*.06)*rr,300+Math.sin(a+t*.06)*rr*.65,3+i%3,'#e6d7a0')}}
 if(t<14){let a=phase(t,8,10),z=phase(t,12,14);star(1060*(1-z)+640*z,180*(1-z)+350*z,16*(1-z)+30*z,'#f5d474');if(a>0){ctx.globalAlpha=a;line(950,160,1020,176,'#f6e2a7',2);ctx.globalAlpha=1}}
 if(t>=14){let p=phase(t,14,17);ctx.globalAlpha=p;for(let i=0;i<20;i++){let a=i*Math.PI/10;star(640+Math.cos(a)*p*420,350+Math.sin(a)*p*220,7+i%4,['#e9bb58','#ee7751','#d3d7a9'][i%3])}text(S.endline,640,145,54,'#eee9d9','center',700);ctx.globalAlpha=1;y=350+Math.sin(t*5)*8}
 ball(x,y,37,t,t>12);text(S.title,55,42,20,titleColor);let s=S.scenes.findLast(s=>t>=s.start);text(s.text,640,652,25,titleColor,'center');
});
