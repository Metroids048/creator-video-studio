// Internal adapter. Upstream sources and their licenses are copied into each new candidate.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const ROOT = path.resolve(__dirname, '../..');
const esbuild = require(path.join(ROOT, 'runtime/editor/node_modules/esbuild'));
const puppeteer = require(path.join(ROOT, 'runtime/vibe/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js'));
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const files = dir => fs.readdirSync(dir, {withFileTypes:true}).flatMap(e => e.isDirectory() ? files(path.join(dir,e.name)) : [path.join(dir,e.name)]);

async function main() {
  const [engine, inputFile, output, stillArg, videoArg] = process.argv.slice(2);
  if (!['overlay','table'].includes(engine) || !inputFile || !output) throw Error('engine input output stillSeconds [video] required');
  const input = JSON.parse(fs.readFileSync(inputFile,'utf8'));
  const mediaSources=[];
  const still = Number(stillArg ?? 2);
  let width=1920,height=1080,fps=30,duration;
  if (engine === 'overlay') {
    if (input.version !== 1 || !Array.isArray(input.cards) || !input.cards.length) throw Error('Overlay version 1 and nonempty cards required');
    const ids = new Set();
    for (const c of input.cards) {
      if (!c.id || ids.has(c.id) || !Number.isFinite(c.start) || !Number.isFinite(c.end) || c.start < 0 || c.end <= c.start || !c.params || typeof c.params !== 'object') throw Error('Invalid card identity/time/params');
      ids.add(c.id);
    }
    for(const c of input.cards) for(const [key,value] of Object.entries(c.params)) {
      if(!['cam','camSrc','src','image','imgSrc','mediaSrc'].includes(key)||!value)continue;
      if(c.kind!=='focus-card'||key!=='camSrc'||typeof value!=='string'||/^[a-z]+:/i.test(value)||! /\.(mp4|mov|webm|m4v)$/i.test(value))throw Error('Only local FocusCard camSrc video is supported; remote media is not fetched');
      const source=path.resolve(path.dirname(path.resolve(inputFile)),value);
      if(!fs.statSync(source).isFile())throw Error('Local camera video missing');
      mediaSources.push({card:c.id,source,sha256:sha(source),asset:'assets/cam-'+mediaSources.length+path.extname(source).toLowerCase()});
    }
    duration = Math.max(...input.cards.map(c=>c.end));
  } else {
    const {createScene} = require(path.join(ROOT,'resources/visual-library/upstream/Table-VideoSOP/assets/motion/production-core/scene.cjs'));
    ({width,height,fps,duration}=createScene(input).config);
  }
  if (![width,height,fps,duration,still].every(Number.isFinite) || width<64 || width>3840 || height<64 || height>3840 || fps<1 || fps>60 || duration<=0 || duration>600 || still<0 || still>=duration) throw Error('Invalid dimensions / duration / still time');
  const out=path.resolve(output);
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.mkdirSync(out); // Refuse any existing version, including a failed one.
  const native=path.join(out,'native');fs.mkdirSync(native);
  const upstream=path.join(ROOT,'resources/visual-library/upstream');
  fs.cpSync(path.join(upstream,'overlay-studio'),path.join(native,'overlay-studio'),{recursive:true});
  const table=path.join(native,'Table-VideoSOP');fs.mkdirSync(path.join(table,'assets/motion'),{recursive:true});
  fs.cpSync(path.join(upstream,'Table-VideoSOP/assets/motion/production-core'),path.join(table,'assets/motion/production-core'),{recursive:true});
  for(const name of ['LICENSE','LICENSE-CODE'])fs.copyFileSync(path.join(upstream,'Table-VideoSOP',name),path.join(table,name));
  const tableSource=JSON.parse(fs.readFileSync(path.join(upstream,'Table-VideoSOP/SOURCE.json'),'utf8'));
  tableSource.files=tableSource.files.filter(f=>f.path.startsWith('assets/motion/production-core/')||['LICENSE','LICENSE-CODE'].includes(f.path));
  fs.writeFileSync(path.join(table,'SOURCE.json'),JSON.stringify(tableSource,null,2)+'\n');
  const vidFrames={};
  for(const m of mediaSources) {
    fs.mkdirSync(path.join(out,'assets'),{recursive:true});fs.copyFileSync(m.source,path.join(out,m.asset));
    input.cards.find(c=>c.id===m.card).params.camSrc=m.asset;
    const dir='mediaframes/'+mediaSources.indexOf(m);fs.mkdirSync(path.join(out,dir),{recursive:true});
    const result=spawnSync(path.join(ROOT,'.studio/bin/ffmpeg'),['-v','error','-i',m.source,'-t',String(duration),'-vf','fps='+fps,'-q:v','3',path.join(out,dir,'f_%05d.jpg')],{encoding:'utf8'});
    if(result.status!==0)throw Error(result.stderr);
    const count=fs.readdirSync(path.join(out,dir)).length;if(!count)throw Error('Camera video decoded no frames');
    vidFrames[m.asset]={dir,fps,count,dur:count/fps};
  }
  fs.writeFileSync(path.join(out,'input.json'),JSON.stringify(input,null,2)+'\n');
  fs.cpSync(__dirname,path.join(out,'adapter'),{recursive:true});
  const font=path.join(ROOT,'runtime/lanshu-fonts/notosanssc/NotoSansSC[wght].ttf');
  fs.copyFileSync(font,path.join(out,'font.ttf'));
  fs.copyFileSync(path.dirname(font)+'/OFL.txt',path.join(out,'FONT-LICENSE.txt'));
  const css='@font-face{font-family:StudioSC;src:url(font.ttf)}html,body,#root{margin:0;width:100%;height:100%;overflow:hidden}body{font-family:StudioSC,sans-serif;background:'+(engine==='table'?'#fdf7e4':'transparent')+'}*{--hud-font:StudioSC}';
  fs.writeFileSync(path.join(out,'index.html'),'<!doctype html><meta charset="utf-8"><style>'+css+'</style><link rel="stylesheet" href="bundle.css"><div id="root"></div><script src="bundle.js"></script>');
  await esbuild.build({entryPoints:[path.join(__dirname,'entry.tsx')],bundle:true,outfile:path.join(out,'bundle.js'),platform:'browser',jsx:'automatic',nodePaths:[path.join(ROOT,'runtime/visual-materials/node_modules')],define:{'process.env.NODE_ENV':'"production"'},alias:{'@overlay':path.join(native,'overlay-studio/motion-playground/src'),'@table':path.join(native,'Table-VideoSOP/assets/motion/production-core')},plugins:[{name:'local-fonts',setup(b){b.onLoad({filter:/\/fonts\.ts$/},()=>({contents:'export const CUSTOM_FONTS = ["StudioSC"];',loader:'ts'}));}}]});
  const errors=[];let browser;
  try {
    browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,protocolTimeout:15000,args:['--no-proxy-server','--disable-background-networking','--allow-file-access-from-files','--disable-background-timer-throttling','--run-all-compositor-stages-before-draw']});
    const page=await browser.newPage();await page.setViewport({width,height,deviceScaleFactor:1});
    page.on('pageerror',e=>errors.push(e.message));
    await page.setRequestInterception(true);
    page.on('request',r=> /^(file:|data:|blob:)/.test(r.url()) ? r.continue() : r.abort());
    await page.evaluateOnNewDocument(job=>window.__MATERIAL_JOB=job,{engine,input});
    await page.evaluateOnNewDocument(man=>window.__VID_FRAMES=man,vidFrames);
    await page.evaluateOnNewDocument(()=>Object.defineProperty(window,'__fxClockRate',{get:()=>1,set:()=>{}}));
    await page.goto('file://'+path.join(out,'index.html')+'?export=1',{waitUntil:'load'});
    await page.evaluate(()=>document.fonts.ready);
    if(engine==='overlay') {
      await page.waitForFunction('typeof window.__startExport === "function"',{timeout:10000});
      await page.evaluate(()=>window.__startExport());
    }
    const frames=videoArg==='video'?Math.ceil(duration*fps):Math.floor(still*fps)+1;
    const frameDir=path.join(out,'frames');if(videoArg==='video')fs.mkdirSync(frameDir);
    let state;
    for(let f=0;f<frames;f++) {
      const t=f/fps;
      if(engine==='overlay') {
        // Chrome 157 stalls virtual-time capture. Both hook time and CSS time are explicitly driven here.
        await page.evaluate(t=>window.__setExportT(t),t);
        await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
        await page.evaluate(t=>window.__seekVideos?.(t),t);
        await page.waitForFunction('!window.__pendingVidFrames || window.__pendingVidFrames() === 0',{timeout:5000});
        await page.evaluate(t=>{window.__materialAnimations??=new WeakMap();for(const a of document.getAnimations()){try{if(!window.__materialAnimations.has(a))window.__materialAnimations.set(a,t);a.pause();a.currentTime=Math.max(0,t-window.__materialAnimations.get(a))*1000;}catch{}}},t);
      }
      else state=await page.evaluate(t=>window.__materialFrame(t),t);
      if(videoArg==='video' || f===frames-1) await page.screenshot({path:videoArg==='video'?path.join(frameDir,String(f).padStart(6,'0')+'.png'):path.join(out,'still.png'),omitBackground:engine==='overlay'});
      if(f===Math.floor(still*fps)&&videoArg==='video')fs.copyFileSync(path.join(frameDir,String(f).padStart(6,'0')+'.png'),path.join(out,'still.png'));
      if(f%60===0)console.error('frame',f,'/',frames);
      if(errors.length)throw Error(errors.join('\n'));
    }
    fs.writeFileSync(path.join(out,'available-cards.json'),JSON.stringify(await page.evaluate(()=>window.__MATERIAL_CARDS),null,2));
    if(state)fs.writeFileSync(path.join(out,'semantic-state.json'),JSON.stringify(state,null,2));
    if(videoArg==='video') {
      const filename=engine==='overlay'?'material.webm':'material.mp4';
      const codec=engine==='overlay'?['-c:v','libvpx-vp9','-pix_fmt','yuva420p','-crf','32','-b:v','0','-auto-alt-ref','0','-cpu-used','4']:['-c:v','libx264','-pix_fmt','yuv420p','-crf','18'];
      const result=spawnSync(path.join(ROOT,'.studio/bin/ffmpeg'),['-v','error','-framerate',String(fps),'-i',path.join(frameDir,'%06d.png'),...codec,path.join(out,filename)],{encoding:'utf8'});
      if(result.status!==0)throw Error(result.stderr);
      fs.rmSync(frameDir,{recursive:true});
    }
    fs.writeFileSync(path.join(out,'EDITING.md'),'# 素材候选工程\n\nindex.html 可预览编译画面；input.json 是本次参数；native/ 保留上游源码与许可，adapter/ 保留工作室接线源码。\n修改参数后在工作室根目录用 studio.py visual-build 生成新版本。adapter 使用工作室运行时，不是独立安装包。\nTable 示例只支持三件组件检验/修整/分流；换内容结构须在工作室另做场景适配并验证。\n这些材料未经作品质量审阅，不作为可发布成片。\n');
    const archive=spawnSync('python3',['-c','import pathlib,sys,zipfile\np=pathlib.Path(sys.argv[1])\nwith zipfile.ZipFile(p/"native.zip","w",zipfile.ZIP_DEFLATED) as z:\n for f in p.rglob("*"):\n  if f.is_file() and (f.parts[len(p.parts)] in {"native","adapter","assets","mediaframes"} or f.parent==p and f.name in {"input.json","index.html","bundle.js","bundle.css","font.ttf","FONT-LICENSE.txt","EDITING.md"}): z.write(f,f.relative_to(p))',out],{encoding:'utf8'});
    if(archive.status!==0)throw Error(archive.stderr);
    const nativeId='visual-native';
    const inputs=[{id:nativeId,kind:'native',path:path.join(out,'native.zip'),sha256:sha(path.join(out,'native.zip'))}];
    for(const [name,kind] of [['still.png','image'],[engine==='overlay'?'material.webm':'material.mp4','video']]) if(fs.existsSync(path.join(out,name))) inputs.push({id:'visual-'+kind,kind,path:path.join(out,name),sha256:sha(path.join(out,name)),nativeAsset:nativeId});
    fs.writeFileSync(path.join(out,'studio-inputs.json'),JSON.stringify({inputs},null,2)+'\n');
    const receipt={schema:1,engine,layer_mode:engine==='overlay'?(input.cards.some(c=>c.kind==='focus-card')?'contains_opaque_scene':'transparent_overlay'):'opaque_scene',media_sources:mediaSources,input_sha256:sha(path.join(out,'input.json')),width,height,fps,duration,still_time:Math.floor(still*fps)/fps,source_files:files(native).map(p=>({path:path.relative(out,p),sha256:sha(p)})),adapter_files:files(path.join(out,'adapter')).map(p=>({path:path.relative(out,p),sha256:sha(p)})),outputs:fs.readdirSync(out).filter(p=>/\.(png|mp4|webm|zip)$/.test(p)).map(p=>({path:p,sha256:sha(path.join(out,p))})),quality_status:'unreviewed_material',use:'PNG可作关键画面；studio-inputs.json 经现有素材输入消费并绑定原生ZIP；透明视频需支持alpha的剪辑路线，不放行成片',limitations:engine==='overlay'?'20种公开卡，固定1920×1080；19种可作透明层，FocusCard自带全屏底色，支持本地视频。透明WebM需支持VP9 alpha的工具；剪映MOV沿上游导出。':'MIT示例限三件组件的检验/修整/分流；新关系要改场景源码，不是换字万能模板。'};
    fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
    console.log(JSON.stringify({out,engine,outputs:receipt.outputs,quality_status:receipt.quality_status}));
  } finally {esbuild.stop();if(browser){const proc=browser.process();await Promise.race([browser.close(),new Promise(r=>setTimeout(r,3000))]);if(proc?.exitCode===null)proc.kill('SIGKILL');}}
}
// Dedicated CLI: all renders, writes and child cleanup have completed. Close residual Chrome transport sockets.
main().then(()=>process.stdout.write('',()=>process.exit(0))).catch(e=>{process.stderr.write(e.stack+'\n',()=>process.exit(1));});
