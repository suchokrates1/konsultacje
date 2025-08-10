// Dark mode toggle with persistence
function applyDarkMode(theme) {
  const body = document.body;
  const icon = document.getElementById('darkModeToggle').querySelector('i');
  if (theme === 'dark') {
    body.classList.add('dark-mode');
    icon.classList.remove('bi-moon');
    icon.classList.add('bi-sun');
  } else {
    body.classList.remove('dark-mode');
    icon.classList.remove('bi-sun');
    icon.classList.add('bi-moon');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const darkModeBtn = document.getElementById('darkModeToggle');
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyDarkMode(savedTheme);

  darkModeBtn.addEventListener('click', function () {
    const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyDarkMode(newTheme);
    localStorage.setItem('theme', newTheme);
  });
  const mobileMenu = document.getElementById('mobileMenu');
  if (mobileMenu) {
    mobileMenu.addEventListener('shown.bs.offcanvas', function () {
      const firstLink = mobileMenu.querySelector('a');
      if (firstLink) {
        firstLink.focus();
      }
    });
  }
});
