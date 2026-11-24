import*as THREE from'./three.module.min.js';
import{ctx,S,phase,label,ready,text,line}from'./draw.js';
export {THREE};
export const scene=new THREE.Scene();scene.background=new THREE.Color('#e6e9e5');
export const camera=new THREE.PerspectiveCamera(35,1280/720,.1,100);camera.position.set(10,6,11);camera.lookAt(0,0,0);
export const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(1280,720);renderer.setPixelRatio(1);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
scene.add(new THREE.HemisphereLight('#f5fcff','#65705c',2.2));let key=new THREE.DirectionalLight('#fff1d7',4);key.position.set(-4,9,8);key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-10;key.shadow.camera.right=10;key.shadow.camera.top=10;key.shadow.camera.bottom=-10;key.shadow.bias=-.0004;scene.add(key);let fill=new THREE.DirectionalLight('#adc7ed',1.7);fill.position.set(7,3,-7);scene.add(fill);
export function mat(c,metal=0,rough=.6){return new THREE.MeshStandardMaterial({color:c,metalness:metal,roughness:rough})}
export function mesh(g,m,parent=scene){let o=new THREE.Mesh(g,m);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o}
export function cube(w,h,d,c,parent=scene){return mesh(new THREE.BoxGeometry(w,h,d),typeof c==='string'?mat(c):c,parent)}
export function cylinder(r,len,c,parent=scene,rad=48){let o=mesh(new THREE.CylinderGeometry(r,r,len,rad),typeof c==='string'?mat(c):c,parent);o.rotation.z=Math.PI/2;return o}
export function film(update){ready(t=>{update(t);renderer.render(scene,camera);ctx.drawImage(renderer.domElement,0,0);label(t,S.kind==='voxel-island'&&t>16?'#f3e2bb':S.ink||'#263b43')})}
