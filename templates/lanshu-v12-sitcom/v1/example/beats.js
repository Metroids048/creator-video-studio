/* A three-scene office comedy using the native articulated actor system. */
window.Beats=function(api){
 document.getElementById("caps").style.display="none";
 const actors=[],bubbles=[];
 const dialogue=[['有空吗？帮我看一下？','“一下”到底是多久？'],['五分钟，找出这张图的错字。','这次我知道怎么帮了。'],['目标清楚了，帮忙也轻松了。','把“随便”换成具体一点。']];
 for(let k=0;k<3;k++){
  const st=api.station(k);st.dress.style.display='none';
  const a=api.actor({x:st.cx-390,y:865,s:.88,hair:'bob',shirt:'#df8b81',face:k===0?'worried':'smile',name:'小周'},null,20),b=api.actor({x:st.cx+390,y:865,s:.88,hair:'short',shirt:'#83b5b0',face:k===0?'think':'happy',name:'阿林',flip:true},null,20);actors.push(a,b);
  a.cue(k*10+.8,{arms:['down','point'],face:k===0?'worried':'smile'});b.cue(k*10+5.4,{arms:['chin','down'],face:k===0?'think':'happy'});if(k===2){a.hop(25.5,18,.4);b.cue(25.5,{arms:['cheer','cheer'],face:'proud'});}
  for(let j=0;j<2;j++){
   let L=api.story.lines[k*2+j],B=api.bubble({text:dialogue[k][j],size:42,maxW:650,tail:'down',along:j?.75:.25});B.place(st.cx+(j?230:-230),390);bubbles.push({B,at:L.start,out:L.end});
  }
 }
 return{render(t){actors.forEach(a=>a.render(t));bubbles.forEach(({B,at,out})=>B.render(t,at,out))}};
};
