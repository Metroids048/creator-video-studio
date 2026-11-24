/* Native 3D assembly. MG03's unchanged pure-time motion helpers are a frozen asset.
   New geometry, shot design, product concepts and typography; no reference frames. */
(async () => {
  const D = EVENT_STORY, W = shot.width, H = shot.height;
  const canvas = document.getElementById('frame'); canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  const THREE = await import('./'+shot.localAssets['three-module']);
  const A = await import('./'+shot.localAssets.motion);
  const font = await new FontFace('Tactile', `url(${shot.localAssets['event-font']})`).load();
  document.fonts.add(font);
  const gl = document.createElement('canvas');
  const renderer = new THREE.WebGLRenderer({canvas: gl, antialias: true, preserveDrawingBuffer: true});
  renderer.setSize(W, H); renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#eee9df');
  scene.fog = new THREE.Fog('#eee9df', 22, 65);
  const camera = new THREE.PerspectiveCamera(32, W / H, .1, 100);
  scene.add(new THREE.HemisphereLight('#fff8e9', '#746151', 2.5));
  const sun = new THREE.DirectionalLight('#fff6df', 4); sun.position.set(-3, 8, 5);
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, {left:-7, right:7, top:9, bottom:-5, near:.1, far:30});
  sun.shadow.bias = -.0003; sun.shadow.normalBias = .03; sun.shadow.radius = 3;
  scene.add(sun); scene.add(new THREE.AmbientLight('#ffffff', .35));
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(200,200), new THREE.MeshStandardMaterial({color:'#e8e1d3',roughness:.93}));
  floor.rotation.x = -Math.PI/2; floor.position.y = -.13; floor.receiveShadow = true; scene.add(floor);
  const product = new THREE.Group(); scene.add(product);
  const meshes = new Map();
  for (const o of D.objects) {
    let geometry;
    if (o.shape === 'sphere') { geometry = new THREE.SphereGeometry(1,48,32); geometry.scale(...o.size); }
    else if (o.shape === 'cylinder') geometry = new THREE.CylinderGeometry(o.size[0],o.size[1],o.size[2],64,1,!!o.hollow);
    else if(o.shape === 'torus') geometry = new THREE.TorusGeometry(o.size[0],o.size[1],16,80);
    else geometry = new THREE.BoxGeometry(...o.size);
    const mat = new THREE.MeshStandardMaterial({color:o.color, roughness:o.metal?.32:.66, metalness:o.metal?.72:.02});
    const mesh = new THREE.Mesh(geometry, mat); mesh.castShadow = true; mesh.receiveShadow = true;
    if(o.rotation) mesh.rotation.set(...o.rotation);
    product.add(mesh); meshes.set(o.id, mesh);
  }
  const glow = new THREE.PointLight('#ffbd59', 0, 5); product.add(glow);
  const pool = new THREE.SpotLight('#ffbf62',0,12,Math.PI/3,.65,1);pool.position.set(0,2.5,0);pool.target.position.set(0,0,0);scene.add(pool,pool.target);
  const portrait = H > W, scale = portrait ? W/1080 : H/1080;
  const events = D.events;
  function drawText(text, x, y, size, color='#282d28', align='center') {
    ctx.font=`${size*scale}px Tactile`; ctx.fillStyle=color; ctx.textAlign=align; ctx.fillText(text,x,y);
  }
  function render(frame) {
    frame = Math.max(0,Math.min(D.frames-1,frame));
    for(const o of D.objects) {
      const mesh=meshes.get(o.id), e=events.find(e=>e.object===o.id);
      let u=0;
      if(e && frame>=e.prepare) u=frame<e.contact ? A.easeInOutCubic((frame-e.prepare)/(e.contact-e.prepare)) : 1;
      mesh.position.fromArray(o.from.map((v,i)=>A.lerp(v,o.to[i],u)));
      if(e && frame>=e.contact && frame<e.result) mesh.position.y+=.018*Math.sin((frame-e.contact)/Math.max(1,e.result-e.contact)*Math.PI*2);
      const spin=o.spin||0; mesh.rotation.y=(o.rotation?.[1]||0)+(1-u)*spin;
      if(o.emissive) {
        const on=frame>=D.activation;
        mesh.material.emissive.set(on?'#ffad37':'#000000'); mesh.material.emissiveIntensity=on?1.6:0;
        glow.intensity=on?8:0;pool.intensity=on?9:0; glow.position.copy(mesh.position); glow.position.y-=.25;
      }
    }
    // The camera changes only between authored keys, to reveal the joint/result.
    let key=D.camera.findIndex(k=>k.frame>=frame); if(key<1)key=1;
    const a=D.camera[key-1],b=D.camera[key],u=A.smoother((frame-a.frame)/(b.frame-a.frame));
    const p=a.position.map((v,i)=>A.lerp(v,b.position[i],u));
    camera.position.set(p[0]*1.35,1.6+(p[1]-1.6)*1.35,p[2]*1.35); camera.lookAt(0,1.6,0);
    renderer.render(scene,camera); ctx.drawImage(gl,0,0);
    const left=portrait?90*scale:100*scale, top=portrait?240*scale:100*scale;
    drawText('OBJECT STUDIES  /  '+D.edition,left,top,22,'#6c7168','left');
    drawText(D.title,left,top+80*scale,portrait?58:54,'#222b25','left');
    drawText(D.subtitle,left,top+132*scale,26,'#72766c','left');
    // Event caption appears after physical contact and settled result.
    const active=events.find(e=>frame>=(e.captionFrame??e.result)&&frame<e.end);
    if(active) {
      const y=portrait?H*.79:H*.88;
      drawText(active.caption,W/2,y,portrait?38:34);
      drawText(String(events.indexOf(active)+1).padStart(2,'0')+' / '+String(events.length).padStart(2,'0'),W/2,y+53*scale,22,'#7c806e');
    }
    const progress=frame/(D.frames-1); ctx.fillStyle='#8b9a7a'; ctx.fillRect(left,H-(portrait?240:48)*scale,(W-2*left)*progress,2*scale);
  }
  window.DUR=D.frames/30; window.FPS=30; window.FRAME_FORMAT='png';
  window.eventFrames=events.map(e=>({id:e.id,contact:e.contact,caption:e.captionFrame??e.result}));
  window.renderAt=(t,type='image/png',quality)=>{render(Math.round(t*30));return canvas.toDataURL(type,quality);};
  render(0); window.ready=true;
})().catch(error=>{console.error(error);throw error;});
