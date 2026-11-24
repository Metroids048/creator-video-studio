/* Fictional parcel case. Each pinned exhibit contains visual evidence. */
window.Beats=function(api){
 const rows=[
  [['09:10  取件消息','地点：B 栋侧门 · 柜号 17'],['09:12  实际到达','A 栋正门 · 没有这台柜子']],
  [['核对地址，发现矛盾','取件 B 栋 ≠ 到达 A 栋'],['沿箭头，转到 B 栋侧门','现场柜号：17']],
  [['输入取件码，打开 17 号柜','包裹仍在原位'],['结论：走错楼，并非丢件','虚构案例 · 先核地点']]
 ];
 const svg=(parent,html)=>{let d=document.createElement('div');d.style.cssText='position:absolute;left:45px;top:180px;width:655px;height:220px';d.innerHTML='<svg viewBox="0 0 655 220" width="655" height="220">'+html+'</svg>';parent.append(d);return d};
 const building=(x,label,col)=>`<rect x="${x}" y="15" width="190" height="180" fill="${col}" stroke="#594638" stroke-width="4"/><text x="${x+95}" y="70" text-anchor="middle" font-size="38" fill="#30251c">${label}</text><path d="M${x+75} 195V130H${x+115}V195" fill="#f5eee0" stroke="#594638" stroke-width="4"/>`;
 const boxes=()=>Array.from({length:8},(_,i)=>`<rect x="${40+i%4*110}" y="${10+Math.floor(i/4)*100}" width="100" height="90" fill="${i===5?'#debc77':'#b9c3b4'}" stroke="#594638" stroke-width="4"/><text x="${90+i%4*110}" y="${65+Math.floor(i/4)*100}" font-size="26" text-anchor="middle">${i+12}</text>`).join('');
 const doors=[];
 for(let k=1;k<=3;k++){
  const st=api.station(k);st.tape=false;const cards=[];
  for(let j=0;j<2;j++){
   const at=(k-1)*10+j*5+.2,c=api.card(k,{kind:j?'index':'manila',x:160+j*850,y:235,w:760,h:475,tab:j?'现场复核':'取件记录',pin:j?'blue':'red',at});cards.push(c);
   rows[k-1][j].forEach((s,z)=>api.typed(c.el,s,{x:45,y:55+z*62,size:z?31:38,at:at+.5+z*.7,dur:1}));
   if(k===1&&j===0)svg(c.el,boxes()+'<path d="M535 75 L485 75 L485 155 L270 155" fill="none" stroke="#a42d27" stroke-width="8"/><text x="535" y="55" font-size="34" text-anchor="middle">17</text>');
   if(k===1&&j===1)svg(c.el,building(210,'A 栋','#d9cbae')+'<path d="M470 65l65 65m0-65-65 65" stroke="#a42d27" stroke-width="12"/>');
   if(k===2)svg(c.el,building(40,'A 栋','#d9cbae')+building(420,'B 栋','#b9c3b4')+`<path d="M245 130H395m-25-20 25 20-25 20" fill="none" stroke="${j?'#487966':'#a42d27'}" stroke-width="9"/>`);
   if(k===3&&j===0){const d=svg(c.el,'<rect x="135" y="0" width="360" height="215" fill="#34372f" stroke="#594638" stroke-width="8"/><rect x="220" y="95" width="170" height="110" fill="#c59b63" stroke="#715333" stroke-width="5"/><path d="M220 95l85 45 85-45m-85 45v65" fill="none" stroke="#715333" stroke-width="4"/><g id="door"><rect x="135" y="0" width="360" height="215" fill="#b9c3b4" stroke="#594638" stroke-width="8"/><text x="315" y="115" text-anchor="middle" font-size="52">17</text><circle cx="460" cy="110" r="9" fill="#594638"/></g>');doors.push({e:d.querySelector('#door'),at:21});}
   if(k===3&&j===1)svg(c.el,'<path d="M95 110l70 70L335 15" fill="none" stroke="#487966" stroke-width="18"/><text x="450" y="95" text-anchor="middle" font-size="38">地点核对</text><text x="450" y="155" text-anchor="middle" font-size="34">B 栋 · 17</text>');
   api.stamp(c.el,{text:k===1?'待核':k===2?(j?'位置一致':'地址冲突'):'已找到',tone:k===2&&j===0?'accent':'accent-2',x:585,y:405,size:46,rot:-8,at:at+3.2});
  }
  const [a,b]=api.K.ties(cards[0],cards[1]);api.string(a,b,{at:(k-1)*10+6,dur:.6,tone:k===1?'accent-2':'accent',ends:true});api.focus((k-1)*10+.1,k,{fill:.94});
 }
 return{render(t){doors.forEach(({e,at})=>{const u=Math.max(0,Math.min(1,(t-at)/1.8));e.setAttribute('transform',`translate(135 0) scale(${1-u*.92} 1) translate(-135 0)`);})}};
};
