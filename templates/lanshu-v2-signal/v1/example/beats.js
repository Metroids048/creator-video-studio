/* Fictional four-chunk transport: a visible missing ACK and a selective retry. */
window.Beats=function(api){
 const S=api.story,up=[],lime='#c6f875',muted='#5a6559',red='#f28c75';
 const u=(t,a,d)=>Math.max(0,Math.min(1,(t-a)/d));
 function mk(p,tag,attrs={}){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);p.appendChild(n);return n}
 function text(p,x,y,s,size=34,fill=lime){const n=mk(p,'text',{x,y,fill,'font-family':'Noto Sans SC,sans-serif','font-size':size});n.textContent=s;return n}
 for(let k=0;k<3;k++){
  const z=api.station(k),svg=mk(z,'svg',{width:1920,height:1080,style:'position:absolute;inset:0'}),a=S.chapters[k].start;
  text(svg,140,270,['上传到 75%，为什么不动了？','只补没有确认的那一块','四个确认，文件才完整'][k],54);
  for(const[x,label]of[[180,'本机'],[1390,'接收端']]){mk(svg,'rect',{x,y:380,width:330,height:380,rx:16,fill:'#111d16',stroke:muted,'stroke-width':3});text(svg,x+100,350,label,38)}
  const nodes=[],packets=[],acks=[];
  for(let i=0;i<4;i++){
   const y=425+i*86;mk(svg,'path',{d:`M 510 ${y} H 1390`,fill:'none',stroke:muted,'stroke-width':2,'stroke-dasharray':i===2?'8 8':''});
   text(svg,220,y+12,'块 '+(i+1),34);const n=text(svg,1440,y+12,'等待',30,muted);nodes.push(n);
   packets.push(mk(svg,'rect',{x:510,y:y-14,width:34,height:28,fill:i===2?red:lime}));
   acks.push(text(svg,1100,y-18,'ACK '+(i+1),24,lime));
  }
  const assembled=mk(svg,'g',{}),blocks=[];
  if(k===2){for(let i=0;i<4;i++){blocks.push(mk(assembled,'rect',{x:760,y:480+i*43,width:180,height:34,rx:4,fill:lime}));text(assembled,1010,560,'完整文件',38)}}
  const status=text(svg,610,835,'',40),percent=text(svg,790,365,'0%',58);
  up.push(t=>{
   const local=t-a;let count=0;
   for(let i=0;i<4;i++){
    const retry=k>0&&i===2,known=k>0&&i!==2,go=retry?1.7:.9+i*.55,d=2.8;
    let p=u(local,go,d),ok=known||p>=1;
    if(k===0&&i===2)ok=false;
    nodes[i].textContent=ok?'已确认':i===2&&local>4?'未确认':'等待';nodes[i].setAttribute('fill',ok?lime:i===2?red:muted);
    if(ok)count++;
    const packet=packets[i];packet.setAttribute('x',510+p*850);packet.style.opacity=known||p===0||p===1?'0':'1';
    if(k===0&&i===2&&p>.45)packet.style.opacity='0';
    acks[i].style.opacity=!known&&ok?String(1-u(local,go+d+.5,.8)):'0';
   }
   percent.textContent=(count*25)+'%';status.textContent=k===0?(local>4.5?'缺的是「块 3 的确认」':'逐块发送，逐块确认'):k===1?(local>5?'已收到的三块，不必重传':'块 1、2、4 保留，只重发块 3'):'四块重组 → 文件可用';
   if(k===2){percent.textContent='100%';nodes.forEach(n=>{n.textContent='已确认';n.setAttribute('fill',lime)});packets.forEach(n=>n.style.opacity='0');const q=u(local,2,2);assembled.style.opacity=String(u(local,1.9,.4));blocks.forEach((b,i)=>{b.setAttribute('x',1390+(760-1390)*q);b.setAttribute('y',425+i*86+(480+i*43-425-i*86)*q)});}
  });
 }
 return{render(t){up.forEach(f=>f(t))}};
};
