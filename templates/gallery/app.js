/* Registry data is embedded by templates gallery; this page never starts production. */
const items = JSON.parse(document.querySelector('#catalog').textContent);
const formats = JSON.parse(document.querySelector('#formats').textContent);
const $ = id => document.getElementById(id);
const resource = path => '../../' + path.split('/').map(encodeURIComponent).join('/');
let selected, iframe, video, ready = false, playing = false;
const clock = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
const curationLabel = item => Number.isFinite(item.curation?.score) ? `${item.curation.family} · 主观 ${item.curation.score}/10` : item.sample.label;
function link(parent, text, path) {
  const a = document.createElement('a'); a.textContent = text; a.href = resource(path); a.target = '_blank'; a.rel = 'noopener'; parent.append(a);
}
function state(time, running) {
  playing = running; $('play').textContent = running ? '暂停' : '播放';
  $('seek').value = time; $('time').textContent = `${clock(time)} / ${clock(selected.sample.duration)}`;
}
function command(action, time) {
  if(video) {
    if(action === 'seek') video.currentTime = time;
    if(action === 'play') { if(video.ended) video.currentTime = 0; video.play().catch(e => $('playerStatus').textContent = String(e)); }
    if(action === 'pause') video.pause();
  } else iframe?.contentWindow.postMessage({type:'studio-preview-control', action, time}, '*');
}
function choose(id, scroll = false) {
  const item = items.find(t => t.id === id); if(!item) return;
  selected = item; video?.pause(); video = null; iframe = null; ready = false; playing = false;
  $('play').disabled = true; $('seek').disabled = true; $('seek').max = item.sample.duration; state(0, false);
  $('screen').replaceChildren(); $('screen').classList.toggle('portrait', item.sample.format === '9:16'); $('sound').hidden = !['event-sfx', 'music'].includes(item.sample.audio); $('sound').textContent = '开启声音'; $('playerStatus').textContent = '正在载入本地预览…';
  if(item.sample.kind === 'video') {
    video = document.createElement('video'); video.src = resource(item.sample.path); video.poster = resource(item.sample.poster);
    video.preload = 'metadata'; video.playsInline = true; video.muted = true;
    const current = video;
    video.addEventListener('loadedmetadata', () => { if(video !== current) return; ready = true; $('play').disabled = false; $('seek').disabled = false; const sound = item.sample.audio === 'event-sfx' ? '实录短接触音' : item.sample.audio === 'music' ? '完整音乐' : '静音'; $('playerStatus').textContent = `${item.sample.duration}秒完整新稿 · ${sound}${item.sample.alternate ? ' · 第二份换稿见右侧' : ''}`; });
    for(const event of ['timeupdate','play','pause','ended']) video.addEventListener(event, () => { if(video === current) state(video.currentTime, !video.paused); });
    video.addEventListener('error', () => $('playerStatus').textContent = '样片加载失败，请使用同目录的本机预览启动器。');
    $('screen').append(video);
  } else {
    iframe = document.createElement('iframe'); iframe.title = `${item.name}静音工程演示`;
    iframe.src = resource(item.sample.player); $('screen').append(iframe);
  }
  $('badge').textContent = curationLabel(item); $('title').textContent = item.name;
  $('fit').textContent = `适合：${item.fit}`;
  const eligibility = item.qualification?.production_eligible ? '市场与换稿记录齐备，仍须审本次作品' : `工程储备，待补：${(item.qualification?.gaps || ['有效资格记录']).join('、')}`;
  $('validation').textContent = `${eligibility}。历史样片记录：${item.validation}。${item.limits}`;
  $('links').replaceChildren(); link($('links'), '制作说明', item.entry);
  if(item.market_evidence?.source) { const a=document.createElement('a');a.textContent='对应市场原片';a.href=item.market_evidence.source;a.target='_blank';a.rel='noopener';$('links').append(a); }
  if(item.sample.alternate) link($('links'), '第二份完整新稿', item.sample.alternate);
  if(item.sample.editable) link($('links'), '同版可编辑包', item.sample.editable);
  if(item.sample.brief) link($('links'), '同版制作输入', item.sample.brief);
  if(item.sample.learning_film) link($('links'), '159秒学习复刻（非原创）', item.sample.learning_film);
  if(item.sample.comparison) link($('links'), '原片与复刻对照', item.sample.comparison);
  $('grammar').replaceChildren();
  for(const [label,text] of [['保留',item.adaptation.preserve],['内容编排',item.adaptation.recipe],['替换',item.adaptation.replace.join('；')],['不适合',item.adaptation.avoid]]) {
    const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = text; $('grammar').append(dt,dd);
  }
  $('steps').replaceChildren(); item.adaptation.steps.forEach(s => { const li = document.createElement('li'); li.textContent = s; $('steps').append(li); });
  $('example').textContent = `示例输入：“${item.adaptation.example_request}”`;
  $('sourceLinks').replaceChildren(); link($('sourceLinks'), '样例故事输入', item.sample.story);
  if(item.sample.beats) link($('sourceLinks'), '本片分镜代码', item.sample.beats);
  link($('sourceLinks'), '模板主入口', item.entry);
  document.querySelectorAll('.card').forEach(c => c.setAttribute('aria-pressed', String(c.dataset.id === id)));
  history.replaceState(null, '', '#' + id);
  if(scroll) $('detail').scrollIntoView({behavior: 'smooth', block: 'start'});
}
addEventListener('message', event => {
  if(event.source !== iframe?.contentWindow || event.data?.type !== 'studio-preview-state') return;
  if(event.data.error) { $('playerStatus').textContent = `预览未就绪：${event.data.error}。请用同目录启动器打开。`; return; }
  if(event.data.ready) { ready = true; $('play').disabled = false; $('seek').disabled = false; $('playerStatus').textContent = '45秒静音工程演示 · 可播放或拖动；占位画面需在新任务中演绎'; }
  state(event.data.time, event.data.playing);
});
$('sound').onclick = () => { if(video) { video.muted = !video.muted; $('sound').textContent = video.muted ? '开启声音' : '静音'; } };
$('play').onclick = () => { if(ready) command(playing ? 'pause' : 'play'); };
$('seek').oninput = e => { if(ready) command('seek', Number(e.target.value)); };
for(const [index,item] of items.entries()) {
  const card = document.createElement('button'); card.className = 'card'; card.dataset.id = item.id; card.setAttribute('aria-pressed','false');
  const poster = document.createElement('div'); poster.className = 'poster';
  const img = document.createElement('img'); img.src = resource(item.sample.poster); img.alt = `${item.name}实际演示画面`; img.loading = 'lazy';
  const duration = document.createElement('span'); duration.textContent = `${item.sample.duration}秒 / ${item.sample.audio === 'event-sfx' ? '接触音' : item.sample.audio === 'music' ? '音乐' : '静音'}`;
  poster.append(img,duration); const title = document.createElement('h3'); title.textContent = `${String(index+1).padStart(2,'0')} / ${item.name}`;
  const fit = document.createElement('p'); fit.textContent = item.fit;
  const status = document.createElement('small'); status.textContent = `${curationLabel(item)}${item.curation?.reason ? ' · ' + item.curation.reason : ''}`;
  card.append(poster,title,fit,status); card.onclick = () => choose(item.id,true); $('cards').append(card);
}
for(const category of [...new Set(items.map(t=>t.category))]) { const o=document.createElement('option');o.value=category;o.textContent=category;$('category').append(o); }
$('filter').oninput = () => { const q = $('filter').value.trim().toLocaleLowerCase(),category=$('category').value; let count = 0;
  for(const c of $('cards').children) { const t = items.find(t => t.id === c.dataset.id); c.hidden = (category&&category!==t.category)||![t.name,t.fit,t.id,t.category,...t.tags].join(' ').toLocaleLowerCase().includes(q); if(!c.hidden) count++; }
  $('empty').hidden = count !== 0;
};
$('category').onchange=()=>$('filter').dispatchEvent(new Event('input'));
async function route() {
  const topic = $('request').value.trim(), script = $('script').value;
  $('routes').replaceChildren();
  if(!topic || !script.trim()) { $('routes').textContent = '请填主题和完整文案，再查看匹配。'; return; }
  $('route').disabled = true; $('routes').textContent = '正在核对内容、形式、画幅和同类原作证据…';
  try {
    const response = await fetch('/api/templates/match', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({topic,script,format:$('format').value})});
    const result = await response.json();
    if(!response.ok) throw new Error(result.error || '路由失败');
    $('routes').replaceChildren();
    const note=document.createElement('p');
    note.textContent=result.candidates.length ? '以下候选具备近期原片与工程复用审阅记录；本次故事、动作和声音仍须实际验证。' : result.engineering_candidates.length ? '找到工程候选，但近期原片或实际复用方法尚不成立，当前不能直接扩整片。' : '当前没有与全文和画幅兼容的模板。';
    $('routes').append(note);
    const qualified=new Set(result.candidates.map(t=>t.id));
    const candidates=[...result.candidates,...result.engineering_candidates.filter(t=>!qualified.has(t.id))];
    for(const item of candidates) {
      const button=document.createElement('button'); button.dataset.template=item.id;
      button.textContent=`${qualified.has(item.id)?'市场与复用记录齐备':'仅工程候选'}：${item.name}`;
      const detail=document.createElement('small');
      detail.textContent=`近期对标 ${item.market.confirmed_count}/2 · 方法 ${item.production_evidence?.qualified ? '记录齐备' : (item.production_evidence?.reason || '缺失')} · 标签线索（非语义适配）：${[...item.track_evidence,...item.grammar_evidence].join('、') || item.matched.join('、')} · ${item.limits}`;
      button.append(detail); button.onclick=()=>choose(item.id,true); $('routes').append(button);
    }
    for(const item of result.research_references) {
      const button=document.createElement('button'); button.textContent=`研究配方：${item.name}`;
      button.onclick=()=>{const card=$('format-'+item.id);$('researchFilter').value='';$('researchFamily').value='';$('researchFilter').dispatchEvent(new Event('input'));card.open=true;card.scrollIntoView({behavior:'smooth',block:'center'});};
      $('routes').append(button);
    }
  } catch(error) {
    $('routes').textContent=`无法完成匹配：${error.message}。请通过同目录的本机预览启动器打开。`;
  } finally { $('route').disabled=false; }
}

for(const item of formats) {
  const card=document.createElement('details');card.className='researchCard';card.id='format-'+item.id;card.dataset.id=item.id;
  const title=document.createElement('summary');title.textContent=`${item.name} · ${item.family}`;card.append(title);
  const count=n=>n==null?'未知':Number(n).toLocaleString('zh-CN');
  const market=document.createElement('p');market.className='market';market.textContent=`${item.creator} · 粉丝 ${count(item.market.followers)} · 赞 ${count(item.market.likes)} · 播放 ${count(item.market.views)} · ${item.market.date} · ${item.source_kind} · ${item.market.method}`;card.append(market);
  for(const [label,value] of [['观看回报（判断）',item.viewer_payoff_hypothesis],['画面语法',item.visual_grammar],['换稿',item.replacement_operation],['当前状态',item.implementation]]) {const p=document.createElement('p');p.textContent=`${label}：${value}`;card.append(p);}
  const links=document.createElement('div');links.className='links';const source=document.createElement('a');source.textContent='具体原片';source.href=item.source;source.target='_blank';source.rel='noopener';links.append(source);link(links,'完整配方',item.entry);card.append(links);$('researchCards').append(card);
}
for(const family of [...new Set(formats.map(t=>t.family))]){const o=document.createElement('option');o.value=family;o.textContent=family;$('researchFamily').append(o);}
$('researchFilter').oninput=()=>{const q=$('researchFilter').value.trim().toLocaleLowerCase(),family=$('researchFamily').value;let count=0;for(const c of $('researchCards').children){const t=formats.find(t=>t.id===c.dataset.id);c.hidden=(family&&family!==t.family)||![t.name,t.category,t.creator,...t.tags,t.visual_grammar].join(' ').toLocaleLowerCase().includes(q);if(!c.hidden)count++;}$('researchEmpty').hidden=count!==0;};
$('researchFamily').onchange=()=>$('researchFilter').dispatchEvent(new Event('input'));
$('route').onclick = route; $('request').onkeydown = e => {if(e.key === 'Enter') route();};
choose(location.hash.slice(1) || items[0].id);
