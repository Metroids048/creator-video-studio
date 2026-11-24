/* Adapted from MG06 collage: seeded jit/slap/shadow/torn paper + 12fps cadence.
   Own cut shapes, typography, story, geometry and camera; no sampled reference art. */
(() => {
  const D=EVENT_STORY, W=shot.width, H=shot.height,portrait=H>W;
  const canvas=document.getElementById('frame'); canvas.width=W;canvas.height=H;const X=canvas.getContext('2d');
  const hash=(a,b=0)=>{let h=(a*374761393+b*668265263+1013904223)|0;h=Math.imul(h^(h>>>13),1274126177);h^=h>>>16;return(h>>>0)/4294967296;};
  const clamp=x=>Math.min(1,Math.max(0,x)),lerp=(a,b,u)=>a+(b-a)*u;
  const jit=(id,t,amp=2)=>{const k=Math.floor(t*12+1e-4);return[(hash(id,k)*2-1)*amp,(hash(id+71,k)*2-1)*amp,(hash(id+913,k)*2-1)*amp*.00349];};
  function slap(f,c){const k=Math.floor((f-c)/2.5);if(k<0)return 1+.2*Math.min(1,-k/3);return k===0?.972:k===1?1.01:1;}
  function shadow(lift=0){X.shadowColor='rgba(34,20,8,.23)';X.shadowBlur=8+lift*34;X.shadowOffsetX=3+lift*24;X.shadowOffsetY=6+lift*34;}
  function torn(w,h,seed){X.beginPath();X.moveTo(-w/2,-h/2);for(let i=1;i<=24;i++)X.lineTo(-w/2+w*i/24,-h/2+(hash(seed,i)-.5)*4);X.lineTo(w/2,h/2);for(let i=24;i>=0;i--)X.lineTo(-w/2+w*i/24,h/2+(hash(seed+2,i)-.5)*4);X.closePath();}
  const paper=document.createElement('canvas');paper.width=1080;paper.height=1920;const P=paper.getContext('2d');
  P.fillStyle='#ece4d1';P.fillRect(0,0,1080,1920);
  for(let i=0;i<46000;i++){P.fillStyle=`rgba(72,54,27,${hash(i)*.065})`;P.fillRect(hash(i,2)*1080,hash(i,3)*1920,1,1+hash(i,4)*3);}
  function text(txt,x,y,size,col='#243c46'){X.fillStyle=col;X.font=`${size}px Tactile`;X.textAlign='center';X.fillText(txt,x,y);}
  function icon(o,f){
    if(o.shape==='hidden')return;
    X.fillStyle=o.color||'#e6b54f';X.strokeStyle='#28454c';X.lineWidth=5;X.lineCap='round';X.lineJoin='round';
    if(o.shape==='key'){X.beginPath();X.arc(-35,-25,31,0,Math.PI*2);X.moveTo(-10,-8);X.lineTo(62,65);X.lineTo(75,52);X.moveTo(40,43);X.lineTo(54,29);X.stroke();}
    else if(o.shape==='headphones'){X.beginPath();X.arc(0,-2,63,Math.PI,Math.PI*2);X.stroke();for(const s of[-1,1]){X.fillStyle='#d97257';X.fillRect(s*58-12,-6,24,58);}}
    else if(o.shape==='flower'){for(let i=0;i<5;i++){const a=i/5*Math.PI*2;X.beginPath();X.ellipse(Math.cos(a)*25,Math.sin(a)*25,24,17,a,0,7);X.fill();}X.fillStyle='#d09d34';X.beginPath();X.arc(0,0,18,0,7);X.fill();X.strokeStyle='#537057';X.beginPath();X.moveTo(0,48);X.lineTo(0,112);X.stroke();}
    else if(o.shape==='seal'){X.beginPath();for(let i=0;i<32;i++){const a=i/32*Math.PI*2,r=i%2?49:54;i?X.lineTo(Math.cos(a)*r,Math.sin(a)*r):X.moveTo(r,0);}X.closePath();X.fill();X.fillStyle='#fff5dd';X.font='40px Tactile';X.textAlign='center';X.fillText('赠',0,14);}
    else {torn(o.shape==='letter'?210:145,o.shape==='letter'?140:100,13);X.fill();X.shadowColor='transparent';X.stroke();text(o.label||'',0,13,o.shape==='letter'?32:30);if(o.shape==='letter'){X.strokeStyle='#9fafa6';for(let i=0;i<2;i++){X.beginPath();X.moveTo(-72,35+i*17);X.lineTo(72,35+i*17);X.stroke();}}}
  }
  function draw(frame){
    const f=Math.max(0,Math.min(D.frames-1,frame)),q=Math.floor(f/2.5)*2.5;
    X.setTransform(1,0,0,1,0,0);X.drawImage(paper,0,0,W,H);
    const s=portrait?W/1080:H/1080;
    // Native landscape composes titles left and action right; portrait stacks.
    const cx=portrait?W*.5:W*.64,cy=portrait?H*.49:H*.49;
    let k=D.camera.findIndex(k=>k.frame>=f);if(k<1)k=1;
    const a=D.camera[k-1],b=D.camera[k],u=clamp((q-a.frame)/(b.frame-a.frame)),z=lerp(a.zoom,b.zoom,u*u*(3-2*u));
    X.save();X.translate(cx,cy);X.scale(s*z,s*z);
    const j=jit(D.seed,f/30,.8);X.translate(j[0],j[1]);X.rotate(j[2]);
    // Backing sheet and two real hinge panels. Foreground panels occlude objects.
    X.save();shadow();X.fillStyle=D.layout==='envelope'?'#e2a182':'#a3b8ad';torn(690,620,D.seed);X.fill();X.restore();
    X.strokeStyle='rgba(45,70,65,.2)';X.lineWidth=2;X.setLineDash([9,10]);X.strokeRect(-300,-270,600,540);X.setLineDash([]);
    const fold=D.events.find(e=>e.action==='fold');
    function panels(){const v=f>=fold.contact?1:clamp((q-fold.prepare)/(fold.contact-fold.prepare));
      for(const side of[-1,1]){X.save();X.translate(side*345,0);const width=-350*Math.cos(v*Math.PI);X.fillStyle=side<0?'#e9dcc3':'#f5ecd9';shadow(.1*(1-v));X.beginPath();X.moveTo(0,-305);X.lineTo(-side*width,-245);X.lineTo(-side*width,245);X.lineTo(0,305);X.closePath();X.fill();X.restore();}}
    if(fold&&f<fold.prepare)panels();
    for(const o of D.objects){
      const e=D.events.find(e=>e.object===o.id);if(!e)continue;
      const v=f>=e.contact?1:clamp((q-e.prepare)/(e.contact-e.prepare)),ease=v*v*(3-2*v),pos=o.from.map((n,i)=>lerp(n,o.to[i],ease));
      X.save();X.translate(...pos);X.rotate((1-ease)*(o.rotation||0));X.scale(slap(q,e.contact),slap(q,e.contact));shadow((1-ease)*.5);icon(o,f);X.restore();
    }
    if(fold&&f>=fold.prepare)panels();
    // Paper label is placed after folding, preventing a result spoiler.
    const final=D.events[D.events.length-1];if(f>=final.result){X.save();X.translate(0,30);X.rotate(-.04);shadow();X.fillStyle='#f7eed7';torn(340,95,81);X.fill();X.shadowColor='transparent';text(D.finalLabel,0,14,38);X.restore();}
    X.restore();
    X.save();X.translate(portrait?W*.5:W*.23,portrait?H*.17:H*.3);X.scale(s,s);
    text('PAPER / SMALL RITUALS',0,-75,22,'#7e7665');
    text(D.title,0,0,portrait?58:48);text(D.subtitle,0,61,27,'#6a746a');X.restore();
    const active=D.events.find(e=>f>=(e.captionFrame??e.result)&&f<e.end);
    if(active){X.save();X.translate(portrait?W*.5:W*.64,portrait?H*.79:H*.88);X.scale(s,s);text(active.caption,0,0,portrait?38:34);text(String(D.events.indexOf(active)+1).padStart(2,'0')+' / '+D.events.length,0,52,22,'#8a7e68');X.restore();}
  }
  window.DUR=D.frames/30;window.FPS=30;window.FRAME_FORMAT='png';
  window.renderAt=(t,type='image/png',quality)=>{draw(Math.round(t*30));return canvas.toDataURL(type,quality);};
  new FontFace('Tactile',`url(${shot.localAssets['event-font']})`).load().then(f=>{document.fonts.add(f);draw(0);window.ready=true;});
})();
