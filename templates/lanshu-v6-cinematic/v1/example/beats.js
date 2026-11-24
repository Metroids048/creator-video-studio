/* An umbrella mechanism, performed in the native graphite Three.js studio. */
window.Beats=function(api){
 const {THREE:T}=api,parts=[],cl=x=>Math.max(0,Math.min(1,x)),sm=x=>{x=cl(x);return x*x*(3-2*x)};
 function rod(parent,a,b,r,mat){let m=new T.Mesh(new T.CylinderGeometry(r,r,1,10),mat);parent.add(m);m.castShadow=true;return {m,set(a,b){let d=new T.Vector3().subVectors(b,a);m.position.copy(a).add(b).multiplyScalar(.5);m.scale.y=d.length();m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),d.normalize())}}}
 for(let k=0;k<3;k++){
  const st=api.station(k),g=new T.Group();st.group.add(g);g.rotation.y=-.25;
  const metal=api.mat.metal(),accent=api.mat.accent(),porc=api.mat.porcelain();
  rod(g,null,null,.085,metal).set(new T.Vector3(0,.9,0),new T.Vector3(0,8.5,0));
  const grip=new T.Mesh(new api.RoundedBoxGeometry(.4,1.4,.45,3,.12),porc);grip.position.set(0,1.1,0);grip.castShadow=true;g.add(grip);
  const slider=new T.Mesh(new T.CylinderGeometry(.20,.20,.42,20),accent);g.add(slider);
  const ribs=Array.from({length:12},()=>rod(g,null,null,.035,metal)),struts=Array.from({length:12},()=>rod(g,null,null,.025,porc));
  const geo=new T.BufferGeometry(),arr=new Float32Array(12*9);geo.setAttribute('position',new T.BufferAttribute(arr,3));geo.setIndex(null);
  const canopy=new T.Mesh(geo,new T.MeshStandardMaterial({color:'#d3ae48',roughness:.58,metalness:.08,side:T.DoubleSide,transparent:true,opacity:.86}));canopy.castShadow=true;g.add(canopy);
  const drops=Array.from({length:18},(_,i)=>{let m=new T.Mesh(new T.SphereGeometry(.055,8,6),new T.MeshStandardMaterial({color:'#cbdce4',roughness:.2,metalness:.2}));g.add(m);return m});
  st.fit({x0:-5.3,x1:5.3,y0:.2,y1:10.5});
  api.note(['结构示意：中轴、滑套与伞骨','滑套上推，支撑杆把伞骨展开','伞面展开后，把水引向边缘'][k],k*10+1,k*10+9,{size:32});
  parts.push(t=>{
   const local=t-k*10,open=k===0?.10:k===1?.10+.90*sm((local-1)/4):1,r=.28+4.1*open,tipY=8.25-(2.8-1.1*open),sy=3.4+2.8*open;slider.position.y=sy;
   for(let j=0;j<12;j++){let a=j*Math.PI/6,b=(j+1)*Math.PI/6,v=new T.Vector3(Math.cos(a)*r,tipY,Math.sin(a)*r),mid=new T.Vector3(Math.cos(a)*r*.55,8.25+(tipY-8.25)*.55,Math.sin(a)*r*.55);ribs[j].set(new T.Vector3(0,8.25,0),v);struts[j].set(new T.Vector3(0,sy,0),mid);arr.set([0,8.25,0,v.x,v.y,v.z,Math.cos(b)*r,tipY,Math.sin(b)*r],j*9)}
   geo.attributes.position.needsUpdate=true;geo.computeVertexNormals();canopy.visible=k===2;canopy.material.opacity=.86*sm((local-.2)/1.2);
   drops.forEach((m,j)=>{m.visible=k===2&&local>2;let phase=(Math.max(0,local-2)*.6+j*.073)%1,a=j*2.399;let rr=phase<.65?.8+j%5*.52:2.9+(phase-.65)*4.2;let y=phase<.65?11.6-phase*7:6.7-(phase-.65)*11;m.position.set(Math.cos(a)*rr,y,Math.sin(a)*rr)});
   api.hot(.28,st.at(0,sy,0));
  });
 }
 return{render(t){parts.forEach(f=>f(t))}};
};
