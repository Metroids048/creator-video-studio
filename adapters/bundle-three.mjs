// Package the unchanged upstream module and pinned local Three.js for the
// host compiler, which serves preview HTML at a route without the asset base.
import { readFile, writeFile, rename } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { createHash } from 'node:crypto';
const require=createRequire(import.meta.url);
const root='../runtime/editor/node_modules/esbuild';
const esbuild=require(root);
if(esbuild.version!=='0.25.12')throw new Error('Pinned installed esbuild version changed');
const film=path.resolve(process.argv[2]), file=path.join(film,'index.html');
let html=await readFile(file,'utf8');
const entry=path.join(film,'lib','three-entry.mjs');
const module=html.match(/<script type="module">([\s\S]*?)<\/script>/);
if(module)await writeFile(entry,module[1]);
else if(!html.includes('lib/style-video-three.js'))throw new Error('Expected the upstream inline Three.js entry');
const source=await readFile(entry,'utf8');
const result=await esbuild.build({entryPoints:[entry],bundle:true,write:false,format:'iife',
 platform:'browser',target:'es2022',legalComments:'inline',
 alias:{three:path.join(film,'lib','three','build','three.module.js'),
 'three/addons':path.join(film,'lib','three','addons')}});
const js=result.outputFiles[0].text+'\nfor(const p of Object.values(window.__hf?.buildReady||{})) p.catch(e=>{console.error("style-video 3D initialization failed:",String(e));throw e;});\n';
const output=path.join(film,'lib','style-video-three.js');
await writeFile(output+'.tmp',js);await rename(output+'.tmp',output);
if(module)html=html.replace(module[0],'<script src="lib/style-video-three.js"></script>')
 .replace(/\s*<script type="importmap">[\s\S]*?<\/script>/,'');
await writeFile(file+'.tmp',html);await rename(file+'.tmp',file);
const sha=s=>createHash('sha256').update(s).digest('hex');
await writeFile(path.join(film,'lib','three-bundle.json'),JSON.stringify({
 scope:'Deployment packaging of the upstream entry; no alternate scene engine',
 esbuild:esbuild.version,three:'0.181.2',source_sha256:sha(source),bundle_sha256:sha(js)},null,2));
