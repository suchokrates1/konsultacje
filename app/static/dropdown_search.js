document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('select.form-select').forEach(select => {
    const search = document.createElement('input');
    search.type = 'text';
    search.placeholder = 'Szukaj...';
    search.className = 'form-control mb-2';

    const options = Array.from(select.options);

    search.addEventListener('input', () => {
      const value = search.value.toLowerCase();
      options.forEach(option => {
        const text = option.textContent.toLowerCase();
        option.hidden = !text.includes(value);
      });
    });

    select.parentNode.insertBefore(search, select);
  });
});
