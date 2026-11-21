// Preview forms stay interactive for visual review without submitting data.
document.addEventListener('submit', function (event) {
  if (event.target.method.toLowerCase() === 'get') return;
  event.preventDefault();
  event.stopImmediatePropagation();
  if (event.target.dataset.demoResultUrl) {
    window.location.assign(event.target.dataset.demoResultUrl);
    return;
  }
  const feedback = document.getElementById('ien-preview-feedback');
  feedback.hidden = false;
  feedback.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}, true);
