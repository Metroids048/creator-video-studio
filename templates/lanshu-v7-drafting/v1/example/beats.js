/* A scaled illustrative clearance drawing: the same door and desk, three plans. */
window.Beats=function(api){
 const P=[],ease=(t,a,d)=>{let u=Math.max(0,Math.min(1,(t-a)/d));return u*u*(3-2*u)};
 function e(p,tag,a={},text){let n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(let[k,v]of Object.entries(a))n.setAttribute(k,v);if(text)n.textContent=text;p.appendChild(n);return n}
 for(let k=1;k<=3;k++){
  const F=api.station(k).figs[0],p=F.svg;
  e(p,'rect',{x:420,y:315,width:1060,height:485,fill:'none',stroke:'#e8e8d8','stroke-width':5});
  e(p,'path',{d:'M620 800 H940',stroke:'#070c0f','stroke-width':12});
  e(p,'path',{d:'M940 800 A320 320 0 0 0 620 480',fill:'none',stroke:'#587b91','stroke-width':3,'stroke-dasharray':'12 10'});
  const door=e(p,'line',{x1:620,y1:800,x2:940,y2:800,stroke:'#eed35b','stroke-width':10,'stroke-linecap':'round'});e(p,'circle',{cx:620,cy:800,r:12,fill:'#eed35b'});
  let desk=e(p,'rect',{x:780,y:530,width:275,height:180,fill:'#273b46',stroke:k===0?'#e56c5f':'#e8e8d8','stroke-width':5});
  e(p,'text',{x:1110,y:285,'font-family':'Noto Sans SC','font-size':35,fill:'#e8e8d8'},'桌面  ·  示意尺寸');
  const mark=e(p,'circle',{cx:927.1,cy:710,r:42,fill:'none',stroke:'#e56c5f','stroke-width':5});
  const text=e(p,'text',{x:450,y:875,'font-family':'Noto Sans SC','font-size':40,fill:k===1?'#e56c5f':'#eed35b'},k===1?'转动范围，撞上桌角':k===2?'沿墙移出门的扫掠区':'平面能放下，使用也要能动');
  if(k>=2){e(p,'rect',{x:780,y:530,width:275,height:180,fill:'none',stroke:'#587b91','stroke-width':3,'stroke-dasharray':'9 9'});e(p,'path',{d:'M1060 615 H1330 m-28-20 28 20-28 20',stroke:'#eed35b','stroke-width':5,fill:'none'});}
  P.push(t=>{let a=(k-1)*10,shift=k>=2?380*ease(t,a+1,2.5):0;desk.setAttribute('x',780+shift);let open=ease(t,a+(k===1?.8:4.2),3.2)*(k===1?Math.asin(90/320):Math.PI*.5);door.setAttribute('x2',620+320*Math.cos(open));door.setAttribute('y2',800-320*Math.sin(open));mark.style.opacity=k===1?ease(t,a+4,.5):'0';text.style.opacity=k===1?ease(t,a+3,1):'0'});
 }
 return{render(t){P.forEach(f=>f(t))}};
};
