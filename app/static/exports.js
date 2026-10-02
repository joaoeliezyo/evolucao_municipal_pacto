const exportControl = document.querySelector('.export-control');
if (exportControl) {
  const status = document.getElementById('export-status');
  const buttons = exportControl.querySelectorAll('[data-export-format]');
  let exporting = false;
  let statusTimer;
  buttons.forEach(button => button.addEventListener('click', async () => {
    if (exporting) return;
    exporting = true;
    clearTimeout(statusTimer);
    buttons.forEach(item => {item.disabled = true;});
    status.hidden = false;
    status.textContent = 'Preparando a exportação…';
    try {
      const params = new URLSearchParams(new FormData(document.querySelector('.filters')));
      const response = await fetch(`/api/exports/${button.dataset.exportFormat}?${params}`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(typeof error.detail === 'string' ? error.detail : 'Não foi possível exportar. Tente novamente.');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1]
        || `pacto.${button.dataset.exportFormat === 'png' ? 'zip' : 'pdf'}`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      exportControl.open = false;
      status.textContent = button.dataset.exportFormat === 'png'
        ? 'Download iniciado: ZIP com as três imagens PNG.' : 'Download iniciado: PDF pesquisável com três páginas.';
      statusTimer = setTimeout(() => {status.hidden = true;}, 5000);
    } catch (error) {
      status.textContent = error.message || 'Não foi possível exportar. Tente novamente.';
    } finally {
      exporting = false;
      buttons.forEach(item => {item.disabled = false;});
    }
  }));
  document.addEventListener('click', event => {
    if (!exportControl.contains(event.target)) exportControl.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {exportControl.open = false; exportControl.querySelector('summary').focus();}
  });
}
