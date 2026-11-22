(() => {
  const banner = document.getElementById('cv-analysis-global');
  if (!banner) return;
  const header = document.getElementById('global-nav');
  function updateOffset() {
    if (header?.getBoundingClientRect) banner.style.setProperty('--ien-header-height', Math.ceil(header.getBoundingClientRect().height) + 'px');
  }
  updateOffset();
  if (header && typeof ResizeObserver === 'function') new ResizeObserver(updateOffset).observe(header);
  window.addEventListener?.('resize', () => { updateOffset(); updateSpace(); });
  function updateSpace() {
    if (document.documentElement?.style && banner.getBoundingClientRect) {
      document.documentElement.style.setProperty('--ien-cv-progress-height', banner.hidden ? '0px' : Math.ceil(banner.getBoundingClientRect().height) + 'px');
    }
  }
  if (typeof ResizeObserver === 'function') new ResizeObserver(updateSpace).observe(banner);
  const close = banner.querySelector('[data-cv-progress-dismiss]');
  const key = 'ien-cv-progress-dismissed-' + banner.dataset.userId;
  let dismissedId = null;
  let pendingId = Number(banner.dataset.analysisId) || null;
  try { dismissedId = Number(sessionStorage.getItem(key)) || null; } catch (_) {}
  function update() { banner.hidden = !pendingId || dismissedId === pendingId; updateSpace(); }
  close?.addEventListener('click', () => {
    dismissedId = pendingId;
    try { sessionStorage.setItem(key, String(dismissedId)); } catch (_) {}
    update();
  });
  window.IenCVProgress = {
    setPending(id) { pendingId = Number(id) || null; update(); },
  };
  update();
})();
