/* A new performed chart story. Values are illustrative, not a survey. */
window.Beats=function(api){
 const {story:S}=api, parts=[];
 const ease=(t,a,d)=>{let u=Math.max(0,Math.min(1,(t-a)/d));return u*u*(3-2*u)};
 function el(tag,p,attrs={}){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);p.appendChild(e);return e}
 function txt(p,x,y,text,size=40,color='#292720'){const e=el('text',p,{x,y,'font-family':'Noto Serif SC,serif','font-size':size,fill:color});e.textContent=text;return e}
 const data=[10,10,10,10,10,10,10,10,10,100],red='#b64e3b',ink='#292720';
 for(let k=0;k<3;k++){
  const st=api.station(k),svg=el('svg',st.el,{width:1920,height:1080,viewBox:'0 0 1920 1080',style:'position:absolute;left:0;top:0'});
  txt(svg,120,258,['平均 19，人人接近 19？','把十个数放在同一张图里','多看一个数：中位数'][k],56);
  txt(svg,120,318,'演示数据 · 九个 10，一个 100',30,'#797364');
  el('line',svg,{x1:180,y1:766,x2:1700,y2:766,stroke:ink,'stroke-width':2});
  const bars=data.map((v,i)=>{const r=el('rect',svg,{x:210+i*140,y:766,width:82,height:0,fill:i===9?red:ink});const n=txt(svg,251+i*140,810,String(i+1),24,'#797364');n.setAttribute('text-anchor','middle');return r});
  const labels=data.map((v,i)=>{const e=txt(svg,251+i*140,740,String(v),30,i===9?red:ink);e.setAttribute('text-anchor','middle');return e});
  const mean=el('line',svg,{x1:180,y1:690,x2:1700,y2:690,stroke:red,'stroke-width':3,'stroke-dasharray':'9 8'});
  const m=txt(svg,120,480,k===2?'中位数 = 10':'平均数 = 19',52,red);
  const math=txt(svg,120,385,k===0?'总和 190 ÷ 10 人':k===1?'大多数人，实际都在 10':'从小到大排，第 5、6 个都是 10',38);
  const bracket=el('path',svg,{d:'M 774 840 v 20 h 140 v -20',fill:'none',stroke:red,'stroke-width':4});
  const note=txt(svg,120,555,k===2?'典型位置，补上另一半信息':'一个 100，把平均数拉高了',34,'#797364');
  parts.push(t=>{let a=S.chapters[k].start,u=ease(t,a+.4,2.2);bars.forEach((r,i)=>{const h=4.1*data[i]*ease(t,a+.6+i*.12,1.4);r.setAttribute('y',766-h);r.setAttribute('height',h);labels[i].setAttribute('y',748-h);labels[i].style.opacity=u;if(k===2){r.style.opacity=i===4||i===5?'1':'.22';labels[i].style.opacity=i===4||i===5?'1':'.3'}});math.style.opacity=ease(t,a+1,1);m.style.opacity=ease(t,a+3.5,1);mean.style.opacity=k===2?'0':String(ease(t,a+3.5,1));bracket.style.opacity=k===2?String(ease(t,a+3,1)):'0';note.style.opacity=ease(t,a+5,1);});
  api.push(k,.035);
 }
 return{render(t){parts.forEach(f=>f(t))}};
};
