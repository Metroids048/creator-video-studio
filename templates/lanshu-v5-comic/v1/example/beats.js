/* Six performed panels: an unread interpretation, a kitchen reveal, a reply. */
window.Beats=function(api){
 const S=api.story,P=[],ease=(t,a,d)=>{let u=Math.max(0,Math.min(1,(t-a)/d));return u*u*(3-2*u)};
 function node(p,tag,a={},text){let e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(let[k,v]of Object.entries(a))e.setAttribute(k,v);if(text)e.textContent=text;p.appendChild(e);return e}
 function person(svg,x,y,color,worried=false){let g=node(svg,'g',{transform:`translate(${x} ${y})`});node(g,'path',{d:'M-86 128 Q0 80 86 128 L104 330 H-104Z',fill:color,stroke:'#20252b','stroke-width':9});node(g,'ellipse',{cx:0,cy:0,rx:77,ry:92,fill:'#ffe5c3',stroke:'#20252b','stroke-width':9});node(g,'path',{d:'M-76 -15 Q-95 -105 5 -104 Q100 -100 78 -10 L40 -62 -20 -48 -64 -60Z',fill:'#20252b'});node(g,'circle',{cx:-26,cy:4,r:6,fill:'#20252b'});node(g,'circle',{cx:26,cy:4,r:6,fill:'#20252b'});node(g,'path',{d:worried?'M-33 -25 L-11 -16 M11 -16 L34 -25 M-25 52 Q0 28 25 52':'M-32 -22 H-12 M12 -22 H32 M-27 37 Q0 67 27 37',stroke:'#20252b','stroke-width':7,fill:'none','stroke-linecap':'round'});return g}
 function bubble(svg,x,y,w,lines,tone='#fff'){node(svg,'path',{d:`M${x} ${y} h${w} v128 h-${w*.48} l-34 42 3-42 H${x}Z`,fill:tone,stroke:'#20252b','stroke-width':7});lines.forEach((s,j)=>node(svg,'text',{x:x+28,y:y+52+j*48,'font-family':'Noto Sans SC','font-size':38,fill:'#20252b'},s));}
 for(let i=0;i<6;i++){
  const F=api.frame(i+1),svg=node(F.el,'svg',{width:F.w,height:F.h,viewBox:'0 0 1704 724',style:'position:absolute;inset:0'});
  node(svg,'rect',{x:0,y:0,width:1704,height:724,fill:i===2?'#d8e6ed':'#fff6e1'});
  const floor=node(svg,'path',{d:'M40 630 H1660',stroke:'#20252b','stroke-width':8});
  if(i===0||i===1){person(svg,440,280,'#e57191',i===1);let ph=node(svg,'g',{transform:'translate(760 160)'});node(ph,'rect',{x:0,y:0,width:350,height:435,rx:28,fill:'#20252b'});node(ph,'rect',{x:16,y:36,width:318,height:366,rx:10,fill:'#f8f5e9'});bubble(ph,43,82,234,['周末吃饭吗？'],'#f8d75c');node(ph,'text',{x:220,y:275,'font-size':36,'font-family':'Noto Sans SC',fill:'#747b80'},'已读');if(i===1){bubble(svg,1150,235,480,['是不是……','不想理我？']);node(svg,'path',{d:'M574 101 l32-62 M632 136 l60-25',stroke:'#20252b','stroke-width':10});}}
  if(i===2){const b=person(svg,1130,280,'#70b8d2');node(svg,'rect',{x:300,y:500,width:1160,height:140,fill:'#c89e71',stroke:'#20252b','stroke-width':9});node(svg,'path',{d:'M600 430 H930 L898 535 H633Z',fill:'#596a7c',stroke:'#20252b','stroke-width':8});node(svg,'path',{d:'M670 385 Q630 350 670 305 M765 385 Q725 350 765 305 M860 385 Q820 350 860 305',stroke:'#fff','stroke-width':13,fill:'none'});node(svg,'path',{d:'M1060 405 L973 460 893 451 M1200 410 L1280 470 1320 425',fill:'none',stroke:'#20252b','stroke-width':30,'stroke-linecap':'round'});bubble(svg,260,140,460,['锅里正翻着，','手腾不开。']);}
  if(i===3){person(svg,420,280,'#e57191');bubble(svg,810,180,650,['刚在做饭！','来我家，留了你的份。'],'#bfe5ee');node(svg,'path',{d:'M778 197 l-54 -28 M778 237 l-65 6 M800 158 l-24 -54',stroke:'#20252b','stroke-width':10});}
  if(i===4){person(svg,480,280,'#e57191');bubble(svg,850,230,560,['差点替你编完','一整部内心戏。'],'#f8d75c');node(svg,'path',{d:'M340 150 Q310 115 340 95 M620 160 Q655 135 640 105',stroke:'#e57191','stroke-width':12,fill:'none'});}
  if(i===5){person(svg,450,260,'#e57191');person(svg,1200,260,'#70b8d2');node(svg,'ellipse',{cx:840,cy:555,rx:530,ry:110,fill:'#dab083',stroke:'#20252b','stroke-width':8});[650,1030].forEach(x=>{node(svg,'ellipse',{cx:x,cy:542,rx:105,ry:36,fill:'#fff',stroke:'#20252b','stroke-width':6});node(svg,'path',{d:`M${x-60} 540 q60 -80 120 0`,fill:'#e69555',stroke:'#20252b','stroke-width':5})});bubble(svg,630,50,430,['有些已读，','只是正在生活。']);}
  P.push(t=>{let u=ease(t,S.lines[i].start,.45);svg.style.opacity=u;svg.style.transform=`translateY(${(1-u)*28}px)`;F.cull()});
 }
 api.boom(12.2,7,.2);api.boom(18.2,9,.24);
 return{render(t){P.forEach(f=>f(t))}};
};
