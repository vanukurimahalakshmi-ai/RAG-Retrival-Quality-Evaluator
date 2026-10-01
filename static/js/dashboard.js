let hitVsMissChartInstance = null;
let performanceByKChartInstance = null;
let recallDistChartInstance = null;
let precisionDistChartInstance = null;

let currentK = 5;
let currentDatasetId = '';

document.addEventListener('DOMContentLoaded', () => {
  loadDatasets();
  fetchDashboardMetrics();

  document.getElementById('datasetFilter').addEventListener('change', (e) => {
    currentDatasetId = e.target.value;
    fetchDashboardMetrics();
  });

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.querySelectorAll('.k-label').forEach(el => el.textContent = currentK);
    fetchDashboardMetrics();
  });
});

async function loadDatasets() {
  try {
    const res = await fetch('/api/datasets/');
    const datasets = await res.json();
    const select = document.getElementById('datasetFilter');
    select.innerHTML = '<option value="">All Datasets</option>';
    datasets.forEach(d => {
      select.innerHTML += `<option value="${d.id}">${d.name} (${d.question_count} Qs)</option>`;
    });
  } catch (err) {
    console.error('Failed to load datasets:', err);
  }
}

async function fetchDashboardMetrics() {
  try {
    let url = `/api/metrics/?k=${currentK}`;
    if (currentDatasetId) url += `&dataset_id=${currentDatasetId}`;

    const res = await fetch(url);
    const data = await res.json();

    renderStats(data);
    renderHitVsMissChart(data.hit_vs_miss);
    renderPerformanceByKChart(data.performance_by_k);
    renderRecallDistChart(data.recall_distribution);
    renderPrecisionDistChart(data.precision_distribution);
    renderLowestQuestionsTable(data.lowest_performing_questions);
  } catch (err) {
    console.error('Error fetching metrics:', err);
  }
}

function renderStats(data) {
  document.getElementById('statHitRate').textContent = `${data.hit_rate}%`;
  document.getElementById('statRecall').textContent = data.mean_recall.toFixed(4);
  document.getElementById('statPrecision').textContent = data.mean_precision.toFixed(4);
  document.getElementById('statMRR').textContent = data.mrr.toFixed(4);
  document.getElementById('statTotalQ').textContent = data.total_questions;
  document.getElementById('statPassFail').textContent = `${data.successful_retrievals} Hits / ${data.failed_retrievals} Misses`;
}

function renderHitVsMissChart(hitVsMiss) {
  const ctx = document.getElementById('hitVsMissChart').getContext('2d');
  if (hitVsMissChartInstance) hitVsMissChartInstance.destroy();

  hitVsMissChartInstance = new Chart(ctx, {
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
      plugins: {
        legend: { labels: { color: '#9ca3af' } }
      }
    }
  });
}

function renderPerformanceByKChart(perfData) {
  const ctx = document.getElementById('performanceByKChart').getContext('2d');
  if (performanceByKChartInstance) performanceByKChartInstance.destroy();

  const labels = perfData.map(p => `K=${p.k}`);
  const recallData = perfData.map(p => p.recall);
  const precisionData = perfData.map(p => p.precision);
  const mrrData = perfData.map(p => p.mrr);

  performanceByKChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { label: 'Recall@K', data: recallData, borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3 },
        { label: 'Precision@K', data: precisionData, borderColor: '#06b6d4', backgroundColor: 'transparent', tension: 0.3 },
        { label: 'MRR', data: mrrData, borderColor: '#f59e0b', backgroundColor: 'transparent', tension: 0.3 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' } },
        y: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' }, min: 0, max: 1 }
      },
      plugins: {
        legend: { labels: { color: '#9ca3af' } }
      }
    }
  });
}

function renderRecallDistChart(dist) {
  const ctx = document.getElementById('recallDistChart').getContext('2d');
  if (recallDistChartInstance) recallDistChartInstance.destroy();

  recallDistChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dist.labels,
      datasets: [{
        label: 'Question Count',
        data: dist.counts,
        backgroundColor: '#3b82f6',
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

function renderPrecisionDistChart(dist) {
  const ctx = document.getElementById('precisionDistChart').getContext('2d');
  if (precisionDistChartInstance) precisionDistChartInstance.destroy();

  precisionDistChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dist.labels,
      datasets: [{
        label: 'Question Count',
        data: dist.counts,
        backgroundColor: '#f59e0b',
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

function renderLowestQuestionsTable(questions) {
  const tbody = document.getElementById('lowestQuestionsTable');
  if (!questions || questions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No evaluation questions found.</td></tr>';
    return;
  }

  tbody.innerHTML = questions.map(q => `
    <tr>
      <td><span class="badge-tag">#${q.id}</span></td>
      <td>
        <a href="/questions/${q.id}/" class="text-white text-decoration-none fw-medium hover-blue">
          ${q.question}
        </a>
      </td>
      <td class="text-secondary small">${q.dataset}</td>
      <td>
        ${q.hit ? '<span class="badge-hit"><i class="bi bi-check-circle"></i> Hit</span>' : '<span class="badge-miss"><i class="bi bi-x-circle"></i> Miss</span>'}
      </td>
      <td class="fw-bold ${q.recall > 0.5 ? 'text-success' : 'text-danger'}">${q.recall.toFixed(2)}</td>
      <td class="fw-bold">${q.precision.toFixed(2)}</td>
      <td>${q.first_relevant_rank ? `Rank ${q.first_relevant_rank}` : '<span class="text-muted">N/A</span>'}</td>
      <td>
        <a href="/questions/${q.id}/" class="btn-secondary-custom btn-sm py-1 px-2">
          Inspect <i class="bi bi-arrow-right-short"></i>
        </a>
      </td>
    </tr>
  `).join('');
}
