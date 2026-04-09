// Frame counter + elapsed real-time overlay on .vid-wrap videos.
// Ported from the original index.html script.
document.querySelectorAll('.vid-wrap').forEach(wrap => {
  const v = wrap.querySelector('video');
  const counter = wrap.querySelector('.counter');
  const time = wrap.querySelector('.corner-time');
  if (!v) return;
  const totalFrames = parseInt(v.dataset.frames || '0', 10);
  const realDur = parseFloat(v.dataset.real || '0');
  let speedLabel = '¼× speed';
  let tagSuffix = '';
  if (time) {
    const orig = time.textContent;
    if (orig && orig.includes('½')) speedLabel = '½× speed';
    if (orig) {
      const parts = orig.split(' · ');
      if (parts.length >= 3) tagSuffix = ' · ' + parts.slice(2).join(' · ');
    }
  }
  function tick() {
    if (!v.duration || isNaN(v.duration)) return;
    const frac = Math.min(1, v.currentTime / v.duration);
    if (counter && totalFrames) {
      const idx = Math.min(totalFrames, Math.max(1, Math.floor(frac * totalFrames) + 1));
      counter.textContent = `frame ${idx}/${totalFrames}`;
    }
    if (time && realDur) {
      const realT = (frac * realDur).toFixed(2);
      time.textContent = `t=${realT}s real · ${speedLabel}${tagSuffix}`;
    }
  }
  v.addEventListener('timeupdate', tick);
  v.addEventListener('loadedmetadata', tick);
  v.play().catch(() => {});
});
