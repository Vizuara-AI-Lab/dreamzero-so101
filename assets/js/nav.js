// Sticky nav — highlight the link for the current page.
(function () {
  const path = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  const name = path === '' ? 'index.html' : path;
  document.querySelectorAll('.topnav-links a').forEach(a => {
    const href = (a.getAttribute('href') || '').toLowerCase();
    if (href === name || (name === 'index.html' && (href === '' || href === './' || href === 'index.html'))) {
      a.classList.add('active');
    }
  });
})();
