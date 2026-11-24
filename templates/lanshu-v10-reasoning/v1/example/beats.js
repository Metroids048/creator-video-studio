/* Counted geometry: 1+...+8 paired into an 8 by 9 rectangle. */
window.Beats=function(api){
 const P=[],ease=(t,a,d)=>{let u=Math.max(0,Math.min(1,(t-a)/d));return u*u*(3-2*u)};
 function n(p,tag,a={},text){let e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(let[k,v]of Object.entries(a))e.setAttribute(k,v);if(text)e.textContent=text;p.appendChild(e);return e}
 for(let k=1;k<=3;k++){
  const st=api.station(k),svg=st.svg,dots=[];
  for(let r=0;r<8;r++)for(let c=0;c<9;c++){
   let original=c<=r,co=original?'#b85d76':'#43887f';const dot=n(svg,'circle',{cx:280+c*70,cy:315+r*63,r:17,fill:co});dots.push({e:dot,r,c,original});
  }
  n(svg,'text',{x:1040,y:390,'font-family':'Noto Serif SC','font-size':54,fill:'#3b3332'},k===1?'1 + 2 + … + 8 = ?':k===2?'两份：8 × 9 = 72':'一份：72 ÷ 2 = 36');
  const note=n(svg,'text',{x:1040,y:500,'font-family':'Noto Sans SC','font-size':34,fill:'#776c69'},k===1?'每一行，比上一行多一个点':k===2?'玫红 36 个，青色 36 个':'从逐个数，变成看整体形状');
  const side=n(svg,'path',{d:'M900 295 H934 V775 H900',fill:'none',stroke:'#3b3332','stroke-width':3});n(svg,'text',{x:960,y:570,'font-family':'Noto Serif SC','font-size':42,fill:'#3b3332'},'8');
  n(svg,'path',{d:'M260 790 V802 H860 V790',fill:'none',stroke:'#3b3332','stroke-width':3});n(svg,'text',{x:550,y:846,'font-family':'Noto Serif SC','font-size':38,fill:'#3b3332'},k===1?'每行不同':'9');
  P.push(t=>{let a=(k-1)*10;dots.forEach(d=>{let u=ease(t,a+.5+d.r*.21+(d.original?0:4),.5);d.e.style.opacity=(!d.original&&k===1)?'0':String(u*(k===3&&!d.original?.2:1));d.e.setAttribute('r',17*u)});note.style.opacity=ease(t,a+5,1);side.style.opacity=k===1?'0':'1'});
 }
 return{render(t){P.forEach(f=>f(t))}};
};
