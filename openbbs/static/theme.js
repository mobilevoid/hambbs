(function(){
  const stored = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-bs-theme', stored);
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('theme-toggle');
    if(!toggle) return;
    toggle.checked = stored === 'dark';
    toggle.addEventListener('change', () => {
      const theme = toggle.checked ? 'dark' : 'light';
      document.documentElement.setAttribute('data-bs-theme', theme);
      localStorage.setItem('theme', theme);
    });
  });
})();
