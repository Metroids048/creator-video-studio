import{THREE,scene,camera,mat,mesh,cube,cylinder,film}from'./three-scene.js';
import{S,phase,lerp,ctx,text,line,circle}from'./draw.js';
const steel=mat('#97aaa8',.85,.23),copper=mat('#bc7b43',.72,.3),blue=mat('#3b6e80',.6,.33);
let base=cube(10,.25,4,'#cad1cb');base.position.y=-2.15;
const casing=new THREE.Group();scene.add(casing);
// Open casing is an intentional physical cutaway. No opaque shell hides the parts.
let shell=mesh(new THREE.CylinderGeometry(1.55,1.55,2.5,64,1,true,Math.PI*.25,Math.PI*1.45),blue,casing);shell.rotation.z=Math.PI/2;
for(let x of[-1.15,1.15]){let ring=mesh(new THREE.TorusGeometry(1.55,.09,12,64),steel,casing);ring.rotation.y=Math.PI/2;ring.position.x=x}
for(let i=0;i<8;i++){let a=i*Math.PI/4;let wind=cube(1.75,.28,.46,copper,casing);wind.position.set(0,1.2*Math.cos(a),1.2*Math.sin(a));wind.rotation.x=a}
for(let x of[-.85,.85]){let foot=cube(.4,.7,2.5,blue,casing);foot.position.set(x,-1.75,0)}
const rotor=new THREE.Group();scene.add(rotor);let core=cylinder(.74,1.7,steel,rotor);let axle=cylinder(.17,5.6,steel,rotor);axle.position.x=.8;
for(let i=0;i<12;i++){let a=i*Math.PI/6;let bar=cube(1.8,.09,.14,mat('#627b7b',.8,.3),rotor);bar.position.set(0,.74*Math.cos(a),.74*Math.sin(a));bar.rotation.x=a}
const bearings=[];for(let x of[-1.65,1.65]){let g=new THREE.Group();scene.add(g);let o=mesh(new THREE.TorusGeometry(.52,.18,16,48),steel,g);o.rotation.y=Math.PI/2;for(let i=0;i<8;i++){let a=i*Math.PI/4;let b=mesh(new THREE.SphereGeometry(.13,12,8),mat('#e1e7de',.9,.1),g);b.position.set(0,.52*Math.cos(a),.52*Math.sin(a))}g.position.x=x;bearings.push(g)}
const fan=new THREE.Group();scene.add(fan);fan.position.x=3.25;cylinder(.38,.5,blue,fan);
for(let i=0;i<5;i++){let a=i*Math.PI*2/5;let blade=cube(.12,1.65,.72,mat('#e1dbbb',.35,.35),fan);blade.position.set(.1,1.15*Math.cos(a),1.15*Math.sin(a));blade.rotation.x=a;blade.rotation.y=.2}

film(t=>{let spin=phase(t,7,11)*(t-7)*5;if(t>20)spin=phase(28-t,0,4)*(t-7)*5;rotor.rotation.x=spin;fan.rotation.x=spin;
 let explode=phase(t,13,17)*(1-phase(t,21,25));casing.position.x=-2.4*explode;bearings[0].position.x=-1.65-1.3*explode;bearings[1].position.x=1.65+.5*explode;fan.position.x=3.25+2*explode;
 let a=.62+.16*Math.sin(t*.16);let distance=15+2.2*explode;camera.position.set(Math.cos(a)*distance,5.6+Math.sin(t*.12),Math.sin(a)*distance);camera.lookAt(.4,0,0);
 // Emissive path dots make the final function visible rather than only a static exploded model.
});

// Register deterministic overlay after the shared font/ready promise has completed.
await new Promise(resolve=>{const check=()=>window.READY?resolve():setTimeout(check,10);check()});
const original=window.render;window.render=t=>{original(t);let phaseId=t<7?0:t<13?1:t<21?2:3;
 const labels=[['外壳固定，内部怎样转？',''],['转轴连接叶片，轴承支撑转子。','转轴驱动叶片'],['沿同一轴线拆开，看清相对位置。','外壳与线圈 / 转子与轴 / 轴承 / 叶片'],['装回之后，再看一次完整关系。','外壳固定 · 轴与叶片一起转']];text(labels[phaseId][0],640,110,33,'#243a43','center',700);text(labels[phaseId][1],640,574,19,'#47616a','center');if(phaseId===2){['固定组件','转子','轴承','叶片'].forEach((s,i)=>{let x=230+i*255;text(s,x,535,17,'#345363','center');line(x,520,x,490,'#547986',1)})}};window.render(0);
