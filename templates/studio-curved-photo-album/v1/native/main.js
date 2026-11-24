import*as T from'./three.module.min.js';
const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d'),S=await(await fetch('story.json')).json(),W=1280,H=720;
const ease=x=>(x=Math.max(0,Math.min(1,x)),x*x*(3-2*x));
await document.fonts.load('24px Studio');
const imgs=await Promise.all(S.pages.map(p=>new Promise((ok,no)=>{let i=new Image;i.onload=()=>ok(i);i.onerror=no;i.src=p.photo})));
const pw=3.7,ph=4.6;
function tex(i,side){let c=document.createElement('canvas');c.width=900;c.height=1120;let a=c.getContext('2d');a.fillStyle='#f4eee0';a.fillRect(0,0,900,1120);
 let im=imgs[i],p=S.pages[i];
 if(side==='right'){let x=45,y=53,w=810,h=878,scale=Math.max(w/im.width,h/im.height);a.save();a.beginPath();a.rect(x,y,w,h);a.clip();a.drawImage(im,x+(w-im.width*scale)*.5,y+(h-im.height*scale)*.5,im.width*scale,im.height*scale);a.restore();a.fillStyle='#b7a691';a.fillRect(44,53,1,878);a.font='18px Studio';a.fillStyle='#7f7469';a.fillText(String(i+1).padStart(2,'0'),53,1040);a.font='18px Studio';a.textAlign='right';a.fillText(p.place,844,1040)}
 else{a.fillStyle='#8d7a64';a.font='18px Studio';a.fillText('S L O W   W E E K E N D',78,116);a.fillStyle='#302d29';a.font='56px Studio';a.fillText(p.heading,78,260);a.font='43px Studio';p.lines.forEach((s,j)=>a.fillText(s,78,365+j*74));a.strokeStyle='#cbbca8';a.lineWidth=1;a.beginPath();a.moveTo(80,770);a.lineTo(440,770);a.stroke();a.fillStyle='#8a7864';a.font='19px Studio';a.fillText(S.title,78,825);a.fillText('— '+String(i+1).padStart(2,'0')+' —',78,1028)}
 const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.anisotropy=8;return t}
const ltex=S.pages.map((_,i)=>tex(i,'left')),rtex=S.pages.map((_,i)=>tex(i,'right'));
const scene=new T.Scene();scene.background=new T.Color('#243b3c');const cam=new T.PerspectiveCamera(34,W/H,.1,50);
const rend=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});rend.setSize(W,H);rend.setPixelRatio(1);rend.outputColorSpace=T.SRGBColorSpace;rend.toneMapping=T.ACESFilmicToneMapping;rend.toneMappingExposure=1.15;rend.shadowMap.enabled=true;rend.shadowMap.type=T.PCFSoftShadowMap;
scene.add(new T.HemisphereLight('#f8f4dc','#4b6663',2.1));const light=new T.DirectionalLight('#ffefd0',3.4);light.position.set(-4,7,6);light.castShadow=true;light.shadow.mapSize.set(2048,2048);light.shadow.camera.left=-8;light.shadow.camera.right=8;light.shadow.camera.top=8;light.shadow.camera.bottom=-8;light.shadow.bias=-.0001;scene.add(light);
const book=new T.Group();scene.add(book);book.rotation.z=.045;book.rotation.x=-.05;
function box(w,h,d,col,x,y,z,parent=book){let o=new T.Mesh(new T.BoxGeometry(w,h,d),new T.MeshStandardMaterial({color:col,roughness:.82}));o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o}
box(8,5,.12,'#355851',0,0,-.22);box(7.58,4.72,.16,'#c9bba3',0,0,-.09);for(let i=0;i<12;i++)box(7.56,4.70,.006,i%3===0?'#b8aa93':'#e3d7c2',0,0,-.16+i*.012);
box(.08,4.71,.06,'#7b6956',0,0,.015);
function surface(left){let g=new T.PlaneGeometry(pw,ph,48,12),m=new T.MeshStandardMaterial({map:ltex[0],roughness:.92,side:T.DoubleSide});let mesh=new T.Mesh(g,m);mesh.position.x=left?-pw/2:pw/2;mesh.position.z=.03;mesh.receiveShadow=true;book.add(mesh);let pos=g.attributes.position;for(let j=0;j<pos.count;j++){let x=pos.getX(j)+(left?-pw/2:pw/2);pos.setZ(j,.04+Math.exp(-Math.abs(x)*3)*.12)}g.computeVertexNormals();return mesh}
const left=surface(true),right=surface(false);
const frontG=new T.PlaneGeometry(pw,ph,64,18),backG=frontG.clone();frontG.translate(pw/2,0,0);backG.translate(pw/2,0,0);
const front=new T.Mesh(frontG,new T.MeshStandardMaterial({map:rtex[0],roughness:.92,side:T.FrontSide})),back=new T.Mesh(backG,new T.MeshStandardMaterial({map:ltex[1],roughness:.92,side:T.BackSide}));front.castShadow=back.castShadow=true;book.add(front,back);
function curl(g,q,backside){let a=g.attributes.position;for(let row=0;row<=18;row++)for(let col=0;col<=64;col++){let j=row*65+col,u=col/64,ang=q*Math.PI,arch=Math.sin(q*Math.PI),theta=ang+Math.sin(u*Math.PI)*.26*arch;let x=u*pw*Math.cos(theta),z=u*pw*Math.sin(theta)+.045+Math.sin(u*Math.PI)*.18*arch;
 a.setXYZ(j,x,ph/2-row/18*ph+(u*u*.10*arch),z+(backside?-.001:.001));if(backside)g.attributes.uv.setX(j,1-u)}a.needsUpdate=true;g.attributes.uv.needsUpdate=true;g.computeVertexNormals()}
const table=new T.Mesh(new T.PlaneGeometry(100,100),new T.MeshStandardMaterial({color:'#23403e',roughness:.9}));table.position.z=-.38;table.receiveShadow=true;scene.add(table);
window.DUR=S.duration;window.render=t=>{let idx=Math.min(S.pages.length-1,Math.floor(t/6)),local=t-idx*6,q=ease((local-4.4)/1.6),next=Math.min(idx+1,S.pages.length-1),turn=idx<S.pages.length-1&&local>4.4;
 left.material.map=ltex[idx];right.material.map=turn?rtex[next]:rtex[idx];front.visible=back.visible=turn;front.material.map=rtex[idx];back.material.map=ltex[next];curl(frontG,q,false);curl(backG,q,true);
 // Static page changes at the exact completed turn, matching the back of the leaf.
 let a=ease(t/2),end=ease((t-32)/4);cam.position.set(-.1+Math.sin(t*.09)*.16, -1.65+.2*a,10.0-.45*a+.7*end);cam.lookAt(0,0,0);book.rotation.z=.035+Math.sin(t*.08)*.013;rend.render(scene,cam);ctx.drawImage(rend.domElement,0,0);if(t<2.2){ctx.globalAlpha=1-ease((t-1)/1.2);ctx.fillStyle='#f3e7cb';ctx.font='26px Studio';ctx.textAlign='center';ctx.fillText(S.title,640,43);ctx.globalAlpha=1}};window.READY=true;window.render(0);
