/* A full serial-pen derivation, no prewritten placeholder cards. */
window.Beats=function(api){
 const S=api.story;
 function write(st,x,y,size,text,t,d=.6,color='ink'){
  const e=api.W('kit-serif',st.x+x,st.y+y,size,text);api.write(e,t,d,color);return e;
 }
 const a=api.station(1),b=api.station(2),c=api.station(3);
 write(a,220,200,64,'同样两个优惠',.8,1);
 write(a,240,345,50,'原价 100',2,.7);
 write(a,740,345,50,'减 20',3.1,.7,'accent');
 write(a,1190,345,50,'打八折',4.2,.8,'accent');
 write(a,240,540,48,'顺序不同，结果会一样吗？',5.5,1.5);
 write(a,240,710,30,'演示计算，不代表具体商家规则',7.5,1);
 write(b,220,195,54,'先减，再打折',10.8,.9);
 write(b,260,335,65,'100 − 20 = 80',12,.9);
 write(b,260,470,65,'80 × 0.8 = 64',13.5,1.1,'accent');
 write(b,220,660,54,'先打折，再减',15.3,.9);
 write(b,930,350,65,'100 × 0.8 = 80',16.5,1.1);
 write(b,930,485,65,'80 − 20 = 60',18,1.1,'accent');
 api.draw(`M ${b.x+910} ${b.y+570} H ${b.x+1670}`,19.5,.7,'accent',5);
 write(c,220,195,54,'差的 4，从哪里来？',21.8,1);
 write(c,260,355,62,'20 × 0.8 = 16',23.2,1,'accent');
 write(c,260,500,48,'先减的 20，也被打了八折。',24.8,1.4);
 write(c,260,660,54,'先看优惠顺序，再算到手价。',27,1.7);
 return{render(){}};
};
