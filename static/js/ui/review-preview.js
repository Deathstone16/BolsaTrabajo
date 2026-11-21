// Preview forms stay interactive for visual review without submitting data.
document.addEventListener('submit', function (event) {
  event.preventDefault();
  event.stopImmediatePropagation();
  const feedback = document.getElementById('ien-preview-feedback');
  feedback.hidden = false;
  feedback.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}, true);
