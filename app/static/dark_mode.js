// Dark mode toggle with persistence
function applyDarkMode(isDark) {
  const body = document.body;
  const icon = document.getElementById('darkModeToggle').querySelector('i');
  if (isDark) {
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
  const savedMode = localStorage.getItem('darkMode');
  applyDarkMode(savedMode === 'enabled');

  darkModeBtn.addEventListener('click', function () {
    const isDark = document.body.classList.toggle('dark-mode');
    const icon = darkModeBtn.querySelector('i');
    if (isDark) {
      icon.classList.remove('bi-moon');
      icon.classList.add('bi-sun');
      localStorage.setItem('darkMode', 'enabled');
    } else {
      icon.classList.remove('bi-sun');
      icon.classList.add('bi-moon');
      localStorage.setItem('darkMode', 'disabled');
    }
  });
});
