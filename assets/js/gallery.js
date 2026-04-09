// Interactive gallery state manager (demo.html).
// Loads gallery/manifest.json and drives category filter + sidebar + main video player.
(async function () {
  const shell = document.querySelector('.gallery-shell');
  if (!shell) return;

  const sidebar = shell.querySelector('.gallery-sidebar .gallery-list');
  const main    = shell.querySelector('.gallery-main');
  const titleEl        = main.querySelector('.gm-title');
  const promptEl       = main.querySelector('.mprompt');
  const metaEl         = main.querySelector('.mmeta');
  const promptPillsEl  = main.querySelector('.prompt-pills');
  const camTabsEl      = main.querySelector('.cam-tabs');
  const playerEl       = main.querySelector('.gallery-player video');
  const noteEl         = main.querySelector('.gm-note');
  const filterBarEl    = document.querySelector('.cat-filter-bar');
  const statsStripEl   = document.querySelector('.gallery-stats-strip');

  let manifest = [];
  try {
    const r = await fetch('gallery/manifest.json', { cache: 'no-store' });
    manifest = await r.json();
  } catch (e) {
    sidebar.innerHTML = '<p class="muted" style="font-size:12px">Failed to load manifest.json</p>';
    return;
  }

  // Category metadata. Order matters (drives filter bar + sidebar order).
  const CATEGORIES = [
    { id: 'simple-pick',    label: 'Simple pick',        desc: 'Training and held-out red-cube pick episodes.' },
    { id: 'mid-episode',    label: 'Mid-episode phases', desc: 'Model resumes mid-trajectory at the descend, grasp, or lift phase.' },
    { id: 'pick-place',     label: 'Pick & place',       desc: 'Pick a cube and place it in a container.' },
    { id: 'stack',          label: 'Stack',              desc: 'Stack one cube on top of another.' },
    { id: 'language-novel', label: 'Novel prompts',      desc: 'Same scene, a novel language instruction the model never saw in training.' },
    { id: 'zero-shot',      label: 'Zero-shot task',     desc: 'Completely unseen dataset and task ("box → red bowl") — not in the training mix.' },
  ];

  const TYPE_LABELS = {
    dreamgen: { label: 'Imagined rollout',   short: 'Imagined',   color: '#C96840' },
    policy:   { label: 'Real-robot chunk',   short: 'Policy',     color: '#2E6A99' },
    zeroshot: { label: 'Unseen dataset',     short: 'Zero-shot',  color: '#6A4EA8' },
  };

  const state = {
    activeCategory: 'all',
    activeTag: manifest[0] && manifest[0].tag,
    activeCam: 'front',
  };

  // ========== Stats strip ==========
  function renderStatsStrip() {
    if (!statsStripEl) return;
    const catCount = new Set(manifest.map(m => m.category)).size;
    const dreamgen = manifest.filter(m => m.type === 'dreamgen').length;
    const policy   = manifest.filter(m => m.type === 'policy').length;
    const zeroshot = manifest.filter(m => m.type === 'zeroshot').length;
    statsStripEl.innerHTML = `
      <div class="stat-chip"><span class="stat-num">${manifest.length}</span><span class="stat-lbl">Rollouts</span></div>
      <div class="stat-chip"><span class="stat-num">${catCount}</span><span class="stat-lbl">Capabilities</span></div>
      <div class="stat-chip"><span class="stat-num" style="color:#C96840">${dreamgen}</span><span class="stat-lbl">Imagined rollouts</span></div>
      <div class="stat-chip"><span class="stat-num" style="color:#2E6A99">${policy}</span><span class="stat-lbl">Real-robot chunks</span></div>
      <div class="stat-chip"><span class="stat-num" style="color:#6A4EA8">${zeroshot}</span><span class="stat-lbl">Unseen datasets</span></div>
    `;
  }

  // ========== Filter bar ==========
  function renderFilterBar() {
    if (!filterBarEl) return;
    filterBarEl.innerHTML = '';
    const counts = {};
    manifest.forEach(m => { counts[m.category] = (counts[m.category] || 0) + 1; });

    const allBtn = document.createElement('button');
    allBtn.className = 'cat-chip' + (state.activeCategory === 'all' ? ' active' : '');
    allBtn.innerHTML = `All<span class="count">${manifest.length}</span>`;
    allBtn.addEventListener('click', () => setCategory('all'));
    filterBarEl.appendChild(allBtn);

    CATEGORIES.forEach(c => {
      if (!counts[c.id]) return;
      const b = document.createElement('button');
      b.className = 'cat-chip cat-' + c.id + (state.activeCategory === c.id ? ' active' : '');
      b.innerHTML = `${c.label}<span class="count">${counts[c.id]}</span>`;
      b.addEventListener('click', () => setCategory(c.id));
      filterBarEl.appendChild(b);
    });
  }

  function setCategory(id) {
    state.activeCategory = id;
    const visible = manifest.filter(m => id === 'all' || m.category === id);
    if (visible.length && !visible.find(v => v.tag === state.activeTag)) {
      state.activeTag = visible[0].tag;
    }
    renderFilterBar();
    renderSidebar();
    renderMain();
  }

  // ========== Sidebar ==========
  function renderSidebar() {
    sidebar.innerHTML = '';
    const catsToShow = state.activeCategory === 'all'
      ? CATEGORIES
      : CATEGORIES.filter(c => c.id === state.activeCategory);

    catsToShow.forEach(cat => {
      const items = manifest.filter(m => m.category === cat.id);
      if (!items.length) return;
      const group = document.createElement('div');
      group.className = 'gallery-group';
      const label = document.createElement('div');
      label.className = 'label cat-' + cat.id;
      label.innerHTML = `<span class="dot"></span>${cat.label}<span class="n">${items.length}</span>`;
      group.appendChild(label);

      items.forEach(item => {
        const thumb = document.createElement('div');
        thumb.className = 'gallery-thumb' + (item.tag === state.activeTag ? ' active' : '');
        thumb.dataset.tag = item.tag;
        const typeInfo = TYPE_LABELS[item.type] || { short: '', color: '#8A8278' };
        const typeBadge = item.type
          ? `<span class="type-badge" style="background:${typeInfo.color}18;color:${typeInfo.color};border:1px solid ${typeInfo.color}55">${typeInfo.short}</span>`
          : '';
        thumb.innerHTML = `
          <img src="${item.thumbnail}" alt="${item.tag}" onerror="this.style.opacity=0.3" />
          <div class="txt">
            <div class="ep">${typeBadge} <span class="pk">${item.prompt_kind}</span></div>
            <div class="task">${item.prompt}</div>
          </div>
        `;
        thumb.addEventListener('click', () => selectTag(item.tag));
        group.appendChild(thumb);
      });
      sidebar.appendChild(group);
    });
  }

  // ========== Prompt pills in main panel ==========
  function renderPromptPills(item) {
    // Show alternative rollouts from the same episode (if any).
    const sameEp = manifest.filter(x => x.episode === item.episode);
    promptPillsEl.innerHTML = '';
    if (sameEp.length <= 1) return;

    const hdr = document.createElement('div');
    hdr.style.cssText = 'font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-faint);font-family:var(--font-mono);margin:0 0 6px';
    hdr.textContent = 'Other rollouts of this scene';
    promptPillsEl.appendChild(hdr);

    sameEp.forEach(x => {
      const p = document.createElement('button');
      p.className = 'prompt-pill' + (x.tag === state.activeTag ? ' active' : '');
      const typeInfo = TYPE_LABELS[x.type] || { label: '', color: '#8A8278' };
      p.innerHTML = `<span class="kind" style="color:${typeInfo.color}">${typeInfo.label}</span><span class="pk">${x.prompt_kind}</span>`;
      p.addEventListener('click', () => selectTag(x.tag));
      promptPillsEl.appendChild(p);
    });
  }

  // ========== Camera tabs ==========
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

  // ========== Main panel ==========
  function renderMain() {
    const item = manifest.find(x => x.tag === state.activeTag);
    if (!item) return;
    const catMeta = CATEGORIES.find(c => c.id === item.category);
    // Set the category class on the main panel so the accent border reflects the task.
    main.dataset.cat = item.category || '';
    titleEl.innerHTML = `<span class="cat-tag cat-${item.category}">${catMeta ? catMeta.label : item.category}</span> ${item.task_summary}`;
    promptEl.textContent = '"' + item.prompt + '"';
    const dur = item.duration_sec ? item.duration_sec.toFixed(1) + 's' : '—';
    const typeInfo = TYPE_LABELS[item.type] || { label: item.type || '—', color: '#8A8278' };
    metaEl.innerHTML = `
      <span><span class="tag">mode</span> <span style="color:${typeInfo.color};font-weight:600">${typeInfo.label}</span></span>
      <span><span class="tag">instruction</span> ${item.prompt_kind}</span>
      <span><span class="tag">duration</span> ${dur}</span>
      <span><span class="tag">cameras</span> 3 views</span>
    `;
    renderPromptPills(item);
    renderCamTabs(item);
    updatePlayer(item);
    if (noteEl) {
      const notes = {
        dreamgen: 'Imagined rollout — the model is given only a single initial frame and then hallucinates six seconds of video and joint commands autoregressively, with no further real-world observations.',
        policy:   'Real-robot chunk — one real camera frame in, nine predicted frames and twenty-four joint-action commands out. This is the mode suitable for deployment on a physical SO-101 arm.',
        zeroshot: 'Unseen dataset — the model was never trained on this task or scene. The rollout is raw generalization from the aggregated SO-101 pretraining mix.',
      };
      noteEl.textContent = notes[item.type] || '';
    }
  }

  function selectTag(tag) {
    state.activeTag = tag;
    renderSidebar();
    renderMain();
  }

  renderStatsStrip();
  renderFilterBar();
  renderSidebar();
  renderMain();
})();
