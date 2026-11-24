/* A complete pop-up delivery story. Every line has a performed paper scene. */
window.Beats=function(api){
 const parts=[],S=api.story,cl=x=>Math.max(0,Math.min(1,x)),sm=x=>{x=cl(x);return x*x*(3-2*x)};
 api.css('.delivery-piece{position:absolute;transform-origin:50% 100%;filter:drop-shadow(4px 7px 2px #24313a24)}');
 function piece(sp,dx,y,w,h,body){let e=api.el('div','delivery-piece',`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">${body}</svg>`);api.box(e,sp.x+dx,y,w,h);return {e,sh:api.shadowFor(sp.x+dx,w,45)}}
 for(let i=0;i<6;i++){
  const line=S.lines[i],sp=api.spot(i+1),start=line.start;
  api.camera.frame(i+1,{s:.98,y:560,dx:10,dy:-8,ds:.015});
  const land=piece(sp,-565,694,1130,146,'<path d="M0 45 Q175 0 370 38 L420 146 H0Z M710 38 Q950 0 1130 45 V146 H710Z" fill="#a9b998" stroke="#526850" stroke-width="4"/><path d="M420 44 Q550 16 710 44 V146 H420Z" fill="#8cb6bd"/><path d="M450 80 Q540 52 640 80 M495 110 Q580 85 680 110" fill="none" stroke="#e1ece7" stroke-width="6"/>');
  const home=piece(sp,315,425,220,330,'<path d="M12 125 L110 14 208 125" fill="#bd6651" stroke="#344959" stroke-width="5"/><path d="M30 125 H190 V330 H30Z" fill="#e4d3af" stroke="#344959" stroke-width="5"/><path d="M91 235 H141 V330 H91Z" fill="#344959"/><path d="M65 155 H108 V198 H65Z M132 155 H170 V198 H132Z" fill="#f4e6b0" stroke="#344959" stroke-width="4"/>');
  const bridge=piece(sp,-170,640,360,155,'<path d="M0 95 Q180 -70 360 95 L360 150 Q180 5 0 150Z" fill="#d9bd82" stroke="#5e594d" stroke-width="5"/><path d="M0 95 Q180 -70 360 95" fill="none" stroke="#faf0d8" stroke-width="14"/><path d="M65 58 L65 95 M130 28 L130 65 M200 22 L200 60 M270 46 L270 86" stroke="#88774f" stroke-width="5"/>');
  const truck=piece(sp,-475,610,200,155,'<path d="M10 35 H115 V115 H10Z" fill="#bf6a55" stroke="#344959" stroke-width="5"/><path d="M115 55 H166 L190 90 V115 H115Z" fill="#344959"/><path d="M125 63 H158 L174 88 H125Z" fill="#c9dad6"/><circle cx="48" cy="122" r="23" fill="#344959"/><circle cx="154" cy="122" r="23" fill="#344959"/>'+(i<4?'<path d="M37 0 H90 V35 H37Z" fill="#e6c15d" stroke="#5e594d" stroke-width="4"/><path d="M63 0 V35 M37 16 H90" stroke="#bd6651" stroke-width="6"/>':''));
  const gift=piece(sp,366,620,105,115,'<path d="M8 30 H97 V112 H8Z" fill="#e6c15d" stroke="#5e594d" stroke-width="4"/><path d="M52 30 V112 M8 64 H97" stroke="#bd6651" stroke-width="9"/><path d="M52 30 Q5 -10 18 6 Q25 -8 52 30 Q80 -8 92 7 Q99 20 52 30Z" fill="#bd6651"/>');
  parts.push(t=>{
   const u=t-start;api.standUp(land.e,land.sh,t,start,.7,null,0,360,1500);api.standUp(home.e,home.sh,t,start+.35,.8,null,0,360,1500);
   const bridgeOn=i>=2;api.vis(bridge.e,bridgeOn);api.vis(bridge.sh,bridgeOn);if(bridgeOn)api.standUp(bridge.e,bridge.sh,t,start+(i===2?1.3:.3),1.1,null,0,360,1500);
   api.vis(truck.e,i<5);api.vis(truck.sh,i<5);if(i<5){api.standUp(truck.e,truck.sh,t,start+.5,.5,null,0,360,1500);let travel=i===0?0:i===1?150:i===2?150:i===3?150+530*sm((u-.7)/3.5):690;let r=(travel-205)/360,yy=i===3&&r>0&&r<1?-330*r*(1-r):0;truck.e.style.left=(sp.x-475+travel)+'px';truck.e.style.top=(590+yy)+'px';}
   api.vis(gift.e,i>=4);api.vis(gift.sh,i>=4);if(i>=4)api.standUp(gift.e,gift.sh,t,start+(i===4?1.2:.5),.7,null,0,360,1500);
  });
 }
 return{render(t){parts.forEach(f=>f(t))}};
};
