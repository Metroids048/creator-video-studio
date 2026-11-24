/* A chalk proof by duplication, using native timed strokes and actual figures. */
window.Beats=function(api){
 for(let k=0;k<3;k++){
  const A=api.area(k*2+1),P=A.P,x=A.x+160,y=A.y+90,w=500,h=Math.min(300,A.h-180),at=k*10;
  const tri=`M${x} ${y} V${y+h} H${x+w} Z`;
  api.S(P,tri,'w',6,at+.8,1.4,{sprite:false});
  api.S(P,`M${x} ${y+h+25} H${x+w} m-20-12 20 12-20 12`,'y',4,at+2.5,.5,{sprite:false});
  api.T(P,x+w*.4,y+h+45,42,[['底',at+2.8,at+3.1,'cy']],{sprite:false});
  api.S(P,`M${x-35} ${y} V${y+h}`,'b',4,at+3.1,.5,{sprite:false});
  api.T(P,x-100,y+h*.4,42,[['高',at+3.3,at+3.6,'cb']],{sprite:false});
  if(k>=1){const companion=api.S(P,`M${x} ${y} H${x+w} V${y+h}`,'y',6,at+4.9,1.1,{sprite:false});if(k===2)api.X(P,companion,[x-15,y-15,w+30,h+30],26.0,1.1);api.T(P,x+w+130,y+50,48,[[k===1?'两份相同三角形':'一份 = 一半',at+5.7,at+7,'cy']],{sprite:false});api.T(P,x+w+130,y+145,44,[[k===1?'拼成一个长方形':'面积 = 底 × 高 ÷ 2',at+7,at+8.9,'cw']],{sprite:false});}
  else api.T(P,x+w+130,y+90,48,[['斜边围出的这一半',at+5.4,at+7,'cw']],{sprite:false});
 }
 return{render(t){}};
};
