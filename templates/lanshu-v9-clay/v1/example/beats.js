/* Seed -> sprout -> flower, on the native clay diorama. */
window.Beats=function(api){
 const {THREE:T}=api,parts=[],sm=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)};
 for(let k=0;k<3;k++){
  const st=api.station(k),g=new T.Group();st.group.add(g);
  const pot=api.mesh(new T.CylinderGeometry(2,1.5,2.6,32),api.M('#de9e85'),0,1.3,0,g),soil=api.mesh(new T.CylinderGeometry(1.84,1.84,.25,32),api.M('#8c6c57'),0,2.6,0,g);
  const seed=api.mesh(new T.SphereGeometry(.35,20,14),api.M('#e3c46d'),0,3.4,0,g);seed.scale.set(1,.65,.75);
  const stem=api.mesh(new T.CylinderGeometry(.13,.16,1,12),api.M('#84b18a'),0,3,0,g);
  const leaves=[-1,1].map(s=>{let m=api.mesh(new T.SphereGeometry(1,24,16),api.M('#a8c791'),s*.75,4,s*.1,g);m.scale.set(1,.18,.45);m.rotation.z=s*.55;return m});
  const flower=new T.Group();g.add(flower);flower.position.y=6.2;
  for(let j=0;j<7;j++){let a=j*Math.PI*2/7,m=api.mesh(new T.SphereGeometry(.75,20,14),api.M('#e9a8af'),Math.cos(a)*.8,Math.sin(a)*.8,0,flower);m.scale.set(.65,1,.3);m.rotation.z=a-Math.PI/2}
  api.mesh(new T.SphereGeometry(.44,24,16),api.M('#f1d66d'),0,0,.3,flower);
  const water=Array.from({length:6},()=>api.mesh(new T.SphereGeometry(.12,10,8),api.M('#a1cfda'),0,6,0,g));
  api.cam.station(k,[[k*12+.6,0,2.5,0,19],[k*12+11.5,.3,2.8,0,19]]);
  parts.push(t=>{let u=t-k*12,grow=k===0?0:k===1?sm((u-1)/8):1;seed.visible=k===0;seed.position.y=3.5-1.1*sm((u-1)/3);stem.visible=k>=1;let h=.1+3.2*grow;stem.scale.y=h;stem.position.y=2.7+h/2;leaves.forEach(m=>{m.visible=k>=1;m.scale.set(grow,.18*grow,.45*grow);m.position.y=2.9+1.3*grow});flower.visible=k===2;let bloom=sm((u-1)/4);flower.scale.setScalar(bloom);water.forEach((m,j)=>{m.visible=(k===0&&u>6&&u<10)||(k===1&&u>0&&u<5);let p=(u*.65+j*.17)%1;m.position.set((j%3-1)*.45,6-p*3.4,j%2*.35)});});
 }
 return{render(t){parts.forEach(f=>f(t))}};
};
