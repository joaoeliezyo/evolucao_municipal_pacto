const chartData = document.getElementById('chart-data');
if (chartData) {
  if (typeof Chart === 'undefined') {
    document.getElementById('chart-message').hidden = false;
  } else {
    const series = JSON.parse(chartData.textContent);
    const colors = ['#1558b0','#15803d','#be123c','#7c3aed','#b45309','#0e7490', '#4338ca','#a21caf','#4d7c0f','#c2410c','#334155','#047857'];
    const positionLabels = {
      id: 'positionLabels',
      afterDatasetsDraw(chart) {
        const {ctx} = chart;
        ctx.save();
        ctx.font = 'bold 12px system-ui, sans-serif';
        ctx.fillStyle = '#21135b';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        chart.getDatasetMeta(0).data.forEach((point, index) => {
          const value = chart.data.datasets[0].data[index];
          if (value !== null) ctx.fillText(`${value}º`, point.x, point.y - 13);
        });
        ctx.restore();
      }
    };
    document.querySelectorAll('[data-series]').forEach(canvas => {
      const s = series[Number(canvas.dataset.series)];
      const values = s.values.filter(value => value !== null);
      const low = Math.min(...values), high = Math.max(...values);
      const range = Math.max(high - low, 20);
      new Chart(canvas, {
        type: 'line', plugins: [positionLabels],
        data: {labels: s.labels.map(month => month.slice(0, 3).toLowerCase().replace(/^./, c => c.toUpperCase())),
          datasets: [{label: s.nome, data: s.values, borderColor: '#1e40af',
            backgroundColor: '#1e40af', pointBorderColor: '#1e40af', pointBorderWidth: 2,
            pointRadius: 5, pointHoverRadius: 8, pointHitRadius: 16, borderWidth: 2.5, tension: 0, spanGaps: false, clip: false}]},
        options: {responsive: true, maintainAspectRatio: false,
          interaction: {mode: 'index', intersect: false},
          onHover: (event, elements) => {canvas.style.cursor = elements.length ? 'pointer' : 'default';},
          layout: {padding: {top: 26, left: 20, right: 20}},
          scales: {y: {display: false, reverse: true, min: Math.max(1, low - range * 0.4), max: high + range * 0.6},
            x: {grid: {display: false}, border: {color: '#e8e8ef'},
              ticks: {autoSkip: false, maxRotation: 0, minRotation: 0, padding: 12, color: '#21135b', font: {size: 11, weight: 'bold'}}}},
          plugins: {legend: {display: false}, tooltip: {enabled: true, displayColors: false, callbacks: {title: items => s.labels[items[0].dataIndex], label: item => `Posição ${item.parsed.y}º`}}}}
      });
    });
    const emphasizeHistoryLine = {
      id: 'emphasizeHistoryLine',
      afterEvent(chart, args) {
        if (args.replay) return;
        const event = args.event;
        let focused = null;
        if (args.inChartArea && event.type !== 'mouseout') {
          const {ctx} = chart;
          const ratio = chart.currentDevicePixelRatio;
          ctx.save();
          ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
          ctx.lineWidth = 12;
          ctx.lineCap = 'round';
          ctx.lineJoin = 'round';
          for (let index = 0; index < chart.data.datasets.length; index++) {
            if (!chart.isDatasetVisible(index)) continue;
            const meta = chart.getDatasetMeta(index);
            ctx.beginPath();
            meta.dataset.path(ctx);
            const onLine = ctx.isPointInStroke(event.x * ratio, event.y * ratio);
            const onPoint = meta.data.some(point => !point.skip && point.inRange(event.x, event.y));
            if (onLine || onPoint) {focused = index; break;}
          }
          ctx.restore();
        }
        if (chart.$focusedDataset === focused) return;
        chart.$focusedDataset = focused;
        chart.canvas.style.cursor = focused === null ? 'default' : 'pointer';
        chart.data.datasets.forEach((dataset, index) => {
          const color = colors[index % colors.length];
          const active = index === focused;
          const faded = focused !== null && !active;
          dataset.borderColor = dataset.backgroundColor = faded ? `${color}66` : color;
          dataset.pointBorderColor = dataset.borderColor;
          dataset.borderWidth = active ? 4 : 2;
          dataset.pointRadius = active ? 5 : 3;
          dataset.order = active ? -1 : 0;
        });
        chart.update('none');
        args.changed = true;
      }
    };
    const historyValues = series.flatMap(item => item.values).filter(Number.isFinite);
    const historyTopPadding = Math.max(2, Math.max(1, ...historyValues) * 0.12);
    new Chart(document.getElementById('history-chart'), {
      type: 'line', plugins: [emphasizeHistoryLine],
      data: {labels: series[0]?.labels || [], datasets: series.map((s, i) => ({
        label: s.nome, data: s.values, borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length], borderWidth: 2, pointRadius: 3, spanGaps: false, tension: 0.15
      }))},
      options: {responsive: true, maintainAspectRatio: false,
        interaction: {mode: 'index', intersect: false},
        scales: {y: {reverse: true, min: 1 - historyTopPadding, title: {display: true, text: 'Posição'},
          ticks: {precision: 0, callback: value => value >= 1 ? value : ''},
          grid: {color: context => context.tick.value < 1 ? 'transparent' : '#e5e7eb'}}},
        plugins: {legend: {labels: {
          sort: (a, b) => a.text.localeCompare(b.text, 'pt-BR', {sensitivity: 'base'}),
          generateLabels: chart => Chart.defaults.plugins.legend.labels.generateLabels(chart).map(item => ({
            ...item,
            fontColor: chart.$focusedDataset == null || item.datasetIndex === chart.$focusedDataset
              ? '#172b45' : '#172b4580'
          }))
        }}, tooltip: {filter: item => item.chart.$focusedDataset === item.datasetIndex,
          callbacks: {label: item => `${item.dataset.label}: posição ${item.parsed.y}`}}}}
    });
  }
}
