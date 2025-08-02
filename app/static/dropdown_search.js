document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('select.form-select').forEach((select) => {
    select.classList.add('d-none');

    const wrapper = document.createElement('div');
    wrapper.className = 'dropdown w-100';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'form-select dropdown-toggle text-start';
    button.dataset.bsToggle = 'dropdown';
    button.ariaExpanded = 'false';

    const menu = document.createElement('div');
    menu.className = 'dropdown-menu w-100 p-2';
    menu.style.maxHeight = '300px';
    menu.style.overflowY = 'auto';

    const search = document.createElement('input');
    search.type = 'text';
    search.placeholder = 'Szukaj...';
    search.className = 'form-control mb-2 dropdown-search';
    menu.appendChild(search);

    const optionsContainer = document.createElement('div');
    menu.appendChild(optionsContainer);

    const options = Array.from(select.options).map((option) => {
      const label = document.createElement('label');
      label.className = 'dropdown-item';
      label.appendChild(document.createTextNode(option.textContent));
      if (option.selected) {
        label.classList.add('active');
      }
      optionsContainer.appendChild(label);

      label.addEventListener('click', () => {
        if (select.multiple) {
          option.selected = !option.selected;
          label.classList.toggle('active', option.selected);
        } else {
          select.value = option.value;
          options.forEach(({ label: lbl }) => lbl.classList.remove('active'));
          label.classList.add('active');
          bootstrap.Dropdown.getOrCreateInstance(button).hide();
        }
        updateButtonText();
      });
      return { label, option };
    });

    function updateButtonText() {
      const selected = Array.from(select.selectedOptions).map((o) => o.textContent);
      button.textContent = selected.length ? selected.join(', ') : 'Wybierz...';
    }

    search.addEventListener('input', () => {
      const value = search.value.toLowerCase();
      options.forEach(({ label }) => {
        const text = label.textContent.toLowerCase();
        label.style.display = text.includes(value) ? '' : 'none';
      });
    });

    updateButtonText();

    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(button);
    wrapper.appendChild(menu);
  });
});
