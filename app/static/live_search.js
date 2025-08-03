document.addEventListener('DOMContentLoaded', () => {
  const debounce = (fn, delay = 300) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => fn.apply(null, args), delay);
    };
  };

  document.querySelectorAll('[data-live-search]').forEach(input => {
    const targetSelector = input.dataset.liveSearch;
    const target = document.querySelector(targetSelector);
    if (!target) return;

    const handler = debounce(async () => {
      const params = new URLSearchParams(window.location.search);
      if (input.value) {
        params.set('q', input.value);
      } else {
        params.delete('q');
      }
      const url = `${window.location.pathname}?${params.toString()}`;
      try {
        const resp = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (resp.ok) {
          const html = await resp.text();
          target.innerHTML = html;
        }
      } catch (err) {
        console.error('Live search failed', err);
      }
    });

    input.addEventListener('input', handler);
  });
});
