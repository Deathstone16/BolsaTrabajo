(() => {
  function initialize() {
    document.querySelectorAll('[data-responsive-disclosure]').forEach((details) => {
      const breakpoint = Number(details.dataset.disclosureBreakpoint || 1024);
      const desktop = window.matchMedia(`(min-width: ${breakpoint}px)`);
      const update = () => { details.open = desktop.matches; };
      update();
      desktop.addEventListener('change', update);
      details.addEventListener('toggle', () => {
        if (desktop.matches && !details.open) details.open = true;
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, {once: true});
  else initialize();
})();
