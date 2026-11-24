/* Existing silent kit demos, driven with the same time API as preview-styles.mjs. */
(() => {
  let time = 0, playing = false, last = 0, sent = 0, duration = 45;
  const notify = (extra = {}) => parent.postMessage({type: 'studio-preview-state', time, playing, duration, ...extra}, '*');
  function frame(t) {
    time = Math.max(0, Math.min(duration, t));
    window.__timelines?.main?.pause().seek(time, false);
    window.dispatchEvent(new CustomEvent('hf-seek', {detail: {time}}));
  }
  function fit() {
    document.documentElement.style.cssText += ';width:100%;height:100%;overflow:hidden';
    document.body.style.transformOrigin = '0 0';
    document.body.style.transform = `scale(${Math.min(innerWidth / 1920, innerHeight / 1080)})`;
  }
  addEventListener('resize', fit); fit();
  addEventListener('message', event => {
    if (event.source !== parent || event.data?.type !== 'studio-preview-control' || !window.__galleryReady) return;
    const command = event.data;
    if (command.action === 'seek' && Number.isFinite(command.time)) frame(command.time);
    if (command.action === 'play') { if(time >= duration) frame(0); playing = true; last = performance.now(); }
    if (command.action === 'pause') playing = false;
    notify();
  });
  async function ready() {
    const start = performance.now();
    while (!window.__timelines?.main && !window.__hf?.buildReady) {
      if (performance.now() - start > 20000) throw Error('原生演示未就绪');
      await new Promise(ok => setTimeout(ok, 50));
    }
    await Promise.all(Object.values(window.__hf?.buildReady || {}));
    await document.fonts.ready;
    duration = Number(document.querySelector('[data-composition-id="main"]')?.dataset.duration) || duration;
    document.querySelectorAll('audio').forEach(a => { a.pause(); a.muted = true; });
    window.__galleryReady = true; frame(0); notify({ready: true});
    function tick(now) {
      if (playing) {
        frame(time + (now - last) / 1000);
        if (time >= duration) playing = false;
      }
      last = now;
      if (now - sent > 100) { notify(); sent = now; }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  ready().catch(error => notify({error: String(error)}));
})();
