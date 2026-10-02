const filterForm = document.querySelector('.filters');
if (filterForm) {
  filterForm.addEventListener('change', event => {
    if (event.target.matches('select')) filterForm.requestSubmit();
  });
}
