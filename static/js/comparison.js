let currentK = 5;

document.addEventListener('DOMContentLoaded', () => {
  fetchComparisonData();

  document.getElementById('configASel').addEventListener('change', fetchComparisonData);
  document.getElementById('configBSel').addEventListener('change', fetchComparisonData);

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.querySelectorAll('.k-label').forEach(el => el.textContent = currentK);
    fetchComparisonData();
  });
});

async function fetchComparisonData() {
  const configAId = document.getElementById('configASel').value;
  const configBId = document.getElementById('configBSel').value;

  let url = `/api/comparison/?k=${currentK}`;
  if (configAId) url += `&config_a=${configAId}`;
  if (configBId) url += `&config_b=${configBId}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    populateRetrieverDropdowns(data.all_configs, data.config_a.id, data.config_b.id);
    renderRetrieverCard('A', data.config_a);
    renderRetrieverCard('B', data.config_b);
    renderDifferences(data.differences);
  } catch (err) {
    console.error('Error fetching comparison data:', err);
  }
}

function populateRetrieverDropdowns(configs, selA, selB) {
  const selectA = document.getElementById('configASel');
  const selectB = document.getElementById('configBSel');

  if (selectA.options.length <= 1) {
    selectA.innerHTML = configs.map(c => `<option value="${c.id}" ${c.id === selA ? 'selected' : ''}>${c.name} (${c.embedding_model})</option>`).join('');
  } else {
    selectA.value = selA;
  }

  if (selectB.options.length <= 1) {
    selectB.innerHTML = configs.map(c => `<option value="${c.id}" ${c.id === selB ? 'selected' : ''}>${c.name} (${c.embedding_model})</option>`).join('');
  } else {
    selectB.value = selB;
  }
}

function renderRetrieverCard(prefix, config) {
  document.getElementById(`name${prefix}`).textContent = config.name;
  document.getElementById(`modelBadge${prefix}`).textContent = config.embedding_model;
  document.getElementById(`chunkSize${prefix}`).textContent = config.chunk_size;
  document.getElementById(`overlap${prefix}`).textContent = config.chunk_overlap;
  document.getElementById(`topK${prefix}`).textContent = config.top_k;

  const m = config.metrics;
  document.getElementById(`recall${prefix}`).textContent = m.recall.toFixed(4);
  document.getElementById(`precision${prefix}`).textContent = m.precision.toFixed(4);
  document.getElementById(`hitRate${prefix}`).textContent = `${m.hit_rate}%`;
  document.getElementById(`mrr${prefix}`).textContent = m.mrr.toFixed(4);
}

function renderDifferences(diff) {
  formatDelta('diffRecall', diff.recall_diff, false);
  formatDelta('diffPrecision', diff.precision_diff, false);
  formatDelta('diffHitRate', diff.hit_rate_diff, true);
  formatDelta('diffMRR', diff.mrr_diff, false);
}

function formatDelta(elementId, value, isPercentage) {
  const el = document.getElementById(elementId);
  const formatted = isPercentage ? `${value >= 0 ? '+' : ''}${value}%` : `${value >= 0 ? '+' : ''}${value.toFixed(4)}`;
  el.textContent = formatted;

  if (value > 0) {
    el.className = 'fw-bold fs-4 text-success';
  } else if (value < 0) {
    el.className = 'fw-bold fs-4 text-danger';
  } else {
    el.className = 'fw-bold fs-4 text-muted';
  }
}
