import {mkdtemp, mkdir, writeFile, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import {render} from '../adapters/native-html-shot.mjs';

const root=resolve(import.meta.dirname,'..');
const temporary=await mkdtemp(join(tmpdir(),'studio-opuscar-viewport-'));
try {
  await mkdir(join(temporary,'engine'));
  await writeFile(join(temporary,'shot.json'),JSON.stringify({engine:'opuscar',width:1280,height:720,fps:30,frames:1}));
  await writeFile(join(temporary,'scene.json'),JSON.stringify({entry:'index.html'}));
  await writeFile(join(temporary,'engine/project.json'),JSON.stringify({canvas:{width:1920,height:1080}}));
  await writeFile(join(temporary,'engine/index.html'),`<!doctype html><style>html,body{margin:0;overflow:hidden}canvas{display:block}</style><canvas width="1920" height="1080"></canvas><script>const c=document.querySelector('canvas'),g=c.getContext('2d');window.render=()=>{g.fillStyle='#fff';g.fillRect(0,0,1920,1080);['#f00','#0f0','#00f','#000'].forEach((color,i)=>{g.fillStyle=color;g.fillRect(i%2?1800:0,i>1?960:0,120,120)})};window.DUR=1/30;window.READY=true</script>`);
  const video=join(temporary,'video.mp4');
  await render(temporary,video,join(root,'runtime/vibe/package.json'));
  const pixels=execFileSync(process.env.FFMPEG,['-v','error','-i',video,'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],{maxBuffer:4*1024*1024});
  const points=[[30,30],[1250,30],[30,690],[1250,690]].map(([x,y])=>[...pixels.subarray((y*1280+x)*3,(y*1280+x)*3+3)]);
  const expected=[[255,0,0],[0,255,0],[0,0,255],[0,0,0]];
  if(points.some((p,i)=>p.some((v,c)=>Math.abs(v-expected[i][c])>25))) throw Error('native corners cropped: '+JSON.stringify(points));
  await writeFile(join(temporary,'scene.json'),JSON.stringify({entry:'index.html',capture:'canvas'}));
  const direct=join(temporary,'canvas.mp4');
  await render(temporary,direct,join(root,'runtime/vibe/package.json'));
  const directPixels=execFileSync(process.env.FFMPEG,['-v','error','-i',direct,'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],{maxBuffer:4*1024*1024});
  if(!pixels.equals(directPixels)) throw Error('canvas capture differs from browser screenshot');
  console.log(JSON.stringify({result:'pass',output:[1280,720],corners:points,canvasMatchesScreenshot:true}));
} finally { await rm(temporary,{recursive:true,force:true}); }
