// Initialize Choices.js for select elements with search
// Adds ARIA label to the generated search input for accessibility

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('select[data-choices]').forEach((select) => {
    const instance = new Choices(select, {
      searchEnabled: true,
      shouldSort: false,
    });
    const container = select.nextElementSibling;
    if (container) {
      const searchInput = container.querySelector('input.choices__input');
      if (searchInput) {
        searchInput.setAttribute('aria-label', 'Wyszukaj');
      }
    }
  });
});
