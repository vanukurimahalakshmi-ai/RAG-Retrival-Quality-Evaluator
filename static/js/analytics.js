let chartInstances = {};
let currentK = 5;
let currentDatasetId = '';

document.addEventListener('DOMContentLoaded', () => {
  loadAnalyticsDatasets();
  fetchAnalyticsData();

  document.getElementById('analyticsDatasetSel').addEventListener('change', (e) => {
    currentDatasetId = e.target.value;
    fetchAnalyticsData();
  });

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.querySelectorAll('.k-label').forEach(el => el.textContent = currentK);
    fetchAnalyticsData();
  });
});

async function loadAnalyticsDatasets() {
  try {
    const res = await fetch('/api/datasets/');
    const datasets = await res.json();
    const select = document.getElementById('analyticsDatasetSel');
    select.innerHTML = '<option value="">All Datasets</option>';
    datasets.forEach(d => {
      select.innerHTML += `<option value="${d.id}">${d.name}</option>`;
    });
  } catch (err) {
    console.error('Failed to load datasets', err);
  }
}

async function fetchAnalyticsData() {
  try {
    let url = `/api/analytics/?k=${currentK}`;
    if (currentDatasetId) url += `&dataset_id=${currentDatasetId}`;

    const res = await fetch(url);
    const data = await res.json();

    renderBarChart('aRecallChart', data.recall_distribution, '#3b82f6', 'Recall@K Range');
    renderBarChart('aPrecisionChart', data.precision_distribution, '#06b6d4', 'Precision@K Range');
    renderBarChart('aMrrChart', data.mrr_distribution, '#f59e0b', 'Reciprocal Rank Category');
    renderBarChart('aRankDistChart', data.rank_distribution, '#8b5cf6', 'First Relevant Rank Position');
    renderHitVsMissPie('aHitVsMissChart', data.hit_vs_miss);
    renderPerfByKLine('aPerfByKChart', data.performance_by_k);
  } catch (err) {
    console.error('Error loading analytics charts:', err);
  }
}

function renderBarChart(canvasId, distData, color, labelName) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

  chartInstances[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: distData.labels,
      datasets: [{
        label: labelName,
        data: distData.counts,
        backgroundColor: color,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false }, ticks: { color: '#9ca3af' } },
        y: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af', stepSize: 1 } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderHitVsMissPie(canvasId, hitVsMiss) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

  chartInstances[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Successful Hits', 'Failed Misses'],
      datasets: [{
        data: [hitVsMiss.hits, hitVsMiss.misses],
        backgroundColor: ['#10b981', '#ef4444'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#9ca3af' } } }
    }
  });
}

function renderPerfByKLine(canvasId, perfData) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

  const labels = perfData.map(p => `K=${p.k}`);

  chartInstances[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { label: 'Recall@K', data: perfData.map(p => p.recall), borderColor: '#3b82f6', tension: 0.3 },
        { label: 'Precision@K', data: perfData.map(p => p.precision), borderColor: '#06b6d4', tension: 0.3 },
        { label: 'Hit Rate (%)', data: perfData.map(p => p.hit_rate / 100), borderColor: '#10b981', tension: 0.3 },
        { label: 'MRR', data: perfData.map(p => p.mrr), borderColor: '#f59e0b', tension: 0.3 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' } },
        y: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' }, min: 0, max: 1 }
      },
      plugins: { legend: { labels: { color: '#9ca3af' } } }
    }
  });
}
