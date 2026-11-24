// Photo montage and printed photo essay share only the deterministic frame API.
const D = PHOTO_STORY;
const canvas = document.getElementById('frame');
canvas.width = shot.width; canvas.height = shot.height;
const ctx = canvas.getContext('2d', {alpha:false});
const W = canvas.width, H = canvas.height;
const images = new Map();
window.DUR = D.frames / 30;
window.FPS = 30;
window.FRAME_FORMAT = 'png';
const clamp = n => Math.max(0, Math.min(1, n));
const smooth = n => {n=clamp(n); return n*n*(3-2*n)};

function cover(img, x, y, width, height, scale=1, anchor=[.5,.5], centered=false) {
  const s = Math.max(width/img.width,height/img.height)*scale;
  const iw=img.width*s, ih=img.height*s;
  const dx=centered?Math.max(width-iw,Math.min(0,width/2-anchor[0]*iw)):(width-iw)*anchor[0];
  const dy=centered?Math.max(height-ih,Math.min(0,height/2-anchor[1]*ih)):(height-ih)*anchor[1];
  ctx.drawImage(img,x+dx,y+dy,iw,ih);
}
function contain(img) {
  const s=Math.min(W*.94/img.width,H*.72/img.height);
  ctx.fillStyle='#10141b';ctx.fillRect(0,0,W,H);
  ctx.save();ctx.shadowColor='#000a';ctx.shadowBlur=36;
  ctx.drawImage(img,(W-img.width*s)/2,H*.05+(H*.72-img.height*s)/2,img.width*s,img.height*s);
  ctx.restore();
}
function framePhoto(i, local, alpha=1, zoom=1, smear=0) {
  const scene=D.scenes[i], img=images.get(scene.asset);
  const progress=clamp(local/(scene.end-scene.start));
  ctx.save(); ctx.globalAlpha=alpha;
  ctx.beginPath();ctx.rect(0,0,W,H);ctx.clip();
  const columns=scene.mirror==='x'||scene.mirror==='xy'?2:1;
  const rows=scene.mirror==='xy'?2:1;
  for(let row=0;row<rows;row++)for(let col=0;col<columns;col++) {
    ctx.save();ctx.beginPath();ctx.rect(col*W/columns,row*H/rows,W/columns,H/rows);ctx.clip();
    if(col) {ctx.translate(W,0);ctx.scale(-1,1);}
    if(row) {ctx.translate(0,H);ctx.scale(1,-1);}
    ctx.globalAlpha=alpha;
    if(scene.fit==='contain')contain(img);
    else cover(img,0,0,W,H,(1+progress*.045)*zoom,scene.anchor||[.5,.5],true);
    if(smear>0) {
      // Zoom accumulation keeps the centre crisp while streaking the perimeter.
      for(let n=1;n<=7;n++) {
        ctx.globalAlpha=alpha*.09;
        cover(img,0,0,W,H,(1+progress*.045)*zoom*(1+smear*n/7),scene.anchor||[.5,.5],true);
      }
    }
    ctx.restore();
  }
  ctx.restore();
}
function montage(frame) {
  let i=D.scenes.findIndex(s=>frame<s.end); if(i<0)i=D.scenes.length-1;
  const s=D.scenes[i], local=frame-s.start;
  const span=s.transitionFrames??Math.min(5,Math.floor((s.end-s.start)/4));
  const next = span>0 && s.end-frame < span && i<D.scenes.length-1;
  const enter = span>0 && i>0 && local<span;
  const transition = next ? smooth(1-(s.end-frame)/span) : enter ? smooth(1-local/span) : 0;
  framePhoto(i,local,1,1+transition*.15,transition*.35);
  if(next && transition>.7) framePhoto(i+1,0,(transition-.7)/.3,1.16,.15);
  if(s.caption) {
    const a=Math.min(smooth(local/8),smooth((s.end-frame)/8));
    ctx.save();ctx.globalAlpha=a;
    const gradient=ctx.createLinearGradient(0,H*.65,0,H*.92);
    gradient.addColorStop(0,'#0000');gradient.addColorStop(1,'#0008');
    ctx.fillStyle=gradient;ctx.fillRect(0,H*.65,W,H*.35);
    ctx.textAlign='center';ctx.fillStyle='#fff9ec';
    ctx.font=`${Math.round(W<H?W*.05:H*.054)}px PhotoText`;
    ctx.fillText(s.caption,W*.5,H*.82,W*.82);ctx.restore();
  }
}
function essay(frame) {
  let i=D.scenes.findIndex(s=>frame<s.end);if(i<0)i=D.scenes.length-1;
  const s=D.scenes[i],local=frame-s.start;
  const img=images.get(s.asset), u=clamp(local/(s.end-s.start));
  ctx.fillStyle='#eeece5';ctx.fillRect(0,0,W,H);
  const scale=1+u*.012;
  if(i>0&&local<16) {
    const p=smooth(local/16);
    cover(images.get(D.scenes[i-1].asset),-W*p,0,W,H);
    ctx.save();ctx.shadowColor='#21261c35';ctx.shadowBlur=W*.025;
    cover(img,W*(1-p),0,W,H);ctx.restore();
  } else cover(img,0,0,W,H,scale);
}
window.renderAt = (t, type='image/png', quality=.92) => {
  const frame=Math.min(D.frames-1,Math.max(0,Math.round(t*30)));
  ctx.globalAlpha=1;ctx.fillStyle='#111';ctx.fillRect(0,0,W,H);
  if(D.template==='photo-beat-montage')montage(frame);else essay(frame);
  return canvas.toDataURL(type,quality);
};
(async()=>{
  const font=new FontFace('PhotoText',`url(${shot.localAssets['photo-font']})`);
  await font.load();document.fonts.add(font);
  await Promise.all(D.scenes.map(async s=>{
    const img=new Image(); img.src=shot.localAssets[s.asset];await img.decode();images.set(s.asset,img);
  }));
  window.renderAt(0);window.ready=true;
})();
