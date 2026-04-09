// Interactive gallery state manager (demo.html).
// Loads gallery/manifest.json and drives sidebar + main video player.
(async function () {
  const shell = document.querySelector('.gallery-shell');
  if (!shell) return;

  const sidebar = shell.querySelector('.gallery-sidebar .gallery-list');
  const main = shell.querySelector('.gallery-main');
  const titleEl = main.querySelector('.gm-title');
  const promptEl = main.querySelector('.mprompt');
  const metaEl = main.querySelector('.mmeta');
  const promptPillsEl = main.querySelector('.prompt-pills');
  const camTabsEl = main.querySelector('.cam-tabs');
  const playerEl = main.querySelector('.gallery-player video');
  const noteEl = main.querySelector('.gm-note');

  let manifest = [];
  try {
    const r = await fetch('gallery/manifest.json', { cache: 'no-store' });
    manifest = await r.json();
  } catch (e) {
    sidebar.innerHTML = '<p class="muted" style="font-size:12px">Failed to load manifest.json</p>';
    return;
  }

  // Group by episode number.
  const groups = {};
  manifest.forEach(item => {
    const key = 'ep' + String(item.episode).padStart(3, '0');
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  });

  const state = {
    activeTag: manifest[0] && manifest[0].tag,
    activeCam: 'front',
  };

  const TYPE_LABELS = {
    dreamgen: { label: 'DreamGen', color: '#C96840' },
    policy:   { label: 'Policy',   color: '#2E6A99' },
  };

  // Render sidebar.
  function renderSidebar() {
    sidebar.innerHTML = '';
    Object.keys(groups).sort().forEach(gk => {
      const group = document.createElement('div');
      group.className = 'gallery-group';
      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = gk + ' · ' + (groups[gk][0].task_summary || '');
      group.appendChild(label);
      groups[gk].forEach(item => {
        const thumb = document.createElement('div');
        thumb.className = 'gallery-thumb' + (item.tag === state.activeTag ? ' active' : '');
        thumb.dataset.tag = item.tag;
        const typeInfo = TYPE_LABELS[item.type] || { label: item.type || '', color: '#8A8278' };
        const typeBadge = item.type ? `<span class="type-badge" style="background:${typeInfo.color}20;color:${typeInfo.color};border:1px solid ${typeInfo.color}40">${typeInfo.label}</span>` : '';
        const metric = item.best_match_drift_deg !== undefined
          ? `<span class="metric-badge">${item.best_match_drift_deg.toFixed(0)}° drift</span>`
          : item.action_rmse_deg !== undefined
          ? `<span class="metric-badge">${item.action_rmse_deg.toFixed(1)}° RMSE</span>`
          : '';
        thumb.innerHTML = `
          <img src="${item.thumbnail}" alt="${item.tag}" />
          <div class="txt">
            <div class="ep">${typeBadge} ${item.prompt_kind}</div>
            <div class="task">${item.prompt}</div>
            ${metric}
          </div>
        `;
        thumb.addEventListener('click', () => selectTag(item.tag));
        group.appendChild(thumb);
      });
      sidebar.appendChild(group);
    });
  }

  // Build prompt pills for an episode (all items sharing the episode number).
  function renderPromptPills(item) {
    // Group pills by type
    const sameEp = manifest.filter(x => x.episode === item.episode);
    const dreamgen = sameEp.filter(x => x.type === 'dreamgen');
    const policy = sameEp.filter(x => x.type === 'policy');

    promptPillsEl.innerHTML = '';
    if (dreamgen.length) {
      const hdr = document.createElement('div');
      hdr.style.cssText = 'font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-faint);font-family:var(--font-mono);margin:0 0 4px';
      hdr.textContent = 'DreamGen rollouts';
      promptPillsEl.appendChild(hdr);
    }
    dreamgen.forEach(x => buildPill(x));
    if (policy.length) {
      const hdr = document.createElement('div');
      hdr.style.cssText = 'font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-faint);font-family:var(--font-mono);margin:8px 0 4px';
      hdr.textContent = 'Policy mode (single-chunk)';
      promptPillsEl.appendChild(hdr);
    }
    policy.forEach(x => buildPill(x));
  }

  function buildPill(x) {
    const p = document.createElement('button');
    p.className = 'prompt-pill' + (x.tag === state.activeTag ? ' active' : '');
    p.innerHTML = `<span class="kind">${x.prompt_kind}</span>${x.prompt}`;
    p.addEventListener('click', () => selectTag(x.tag));
    promptPillsEl.appendChild(p);
  }

  // Build camera tabs.
  function renderCamTabs(item) {
    camTabsEl.innerHTML = '';
    const cams = ['front', 'top', 'gripper'];
    cams.forEach(cam => {
      if (!item.videos || !item.videos[cam]) return;
      const t = document.createElement('button');
      t.className = 'cam-tab' + (cam === state.activeCam ? ' active' : '');
      t.textContent = cam;
      t.addEventListener('click', () => {
        state.activeCam = cam;
        renderCamTabs(item);
        updatePlayer(item);
      });
      camTabsEl.appendChild(t);
    });
    if (!item.videos || !item.videos[state.activeCam]) {
      const fallback = Object.keys(item.videos || {})[0];
      if (fallback) state.activeCam = fallback;
    }
  }

  function updatePlayer(item) {
    const src = (item.videos || {})[state.activeCam];
    if (!src) return;
    if (playerEl.getAttribute('src') !== src) {
      playerEl.setAttribute('src', src);
      playerEl.load();
      playerEl.play().catch(() => {});
    }
  }

  function renderMain() {
    const item = manifest.find(x => x.tag === state.activeTag);
    if (!item) return;
    titleEl.textContent = 'Episode ' + item.episode + ' — ' + (item.task_summary || '');
    promptEl.textContent = '"' + item.prompt + '"';
    const dur = item.duration_sec ? item.duration_sec.toFixed(1) + 's' : '—';
    const typeInfo = TYPE_LABELS[item.type] || { label: item.type || '—', color: '#8A8278' };
    let metricHtml = '';
    if (item.best_match_drift_deg !== undefined) {
      metricHtml = `<span><span class="tag">best-match drift</span> ${item.best_match_drift_deg.toFixed(0)}°</span>`;
    } else if (item.action_rmse_deg !== undefined) {
      metricHtml = `<span><span class="tag">action RMSE</span> ${item.action_rmse_deg.toFixed(2)}°</span>`;
    }
    metaEl.innerHTML = `
      <span><span class="tag">type</span> <span style="color:${typeInfo.color}">${typeInfo.label}</span></span>
      <span><span class="tag">episode</span> ${item.episode}</span>
      <span><span class="tag">prompt</span> ${item.prompt_kind}</span>
      <span><span class="tag">duration</span> ${dur}</span>
      ${metricHtml}
    `;
    renderPromptPills(item);
    renderCamTabs(item);
    updatePlayer(item);
    if (noteEl) {
      const notes = {
        dreamgen: 'Autoregressive DreamGen rollout — 60 chunks of imagined video + actions from a single initial frame, no real observations after frame 0. Trimmed to task completion.',
        policy: 'Single-chunk policy mode — one real frame in, 9 predicted frames + 24 action commands out. This is the mode suitable for real-robot deployment.',
      };
      noteEl.textContent = notes[item.type] || '';
    }
  }

  function selectTag(tag) {
    state.activeTag = tag;
    renderSidebar();
    renderMain();
  }

  renderSidebar();
  renderMain();
})();
