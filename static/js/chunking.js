let currentK = 5;

document.addEventListener('DOMContentLoaded', () => {
  loadChunkingAnalysisTable();

  const form = document.getElementById('newConfigForm');
  if (form) {
    form.addEventListener('submit', handleNewConfigSubmit);
  }

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.querySelectorAll('.k-label').forEach(el => el.textContent = currentK);
    loadChunkingAnalysisTable();
  });
});

async function loadChunkingAnalysisTable() {
  const tbody = document.getElementById('chunkingTableBody');
  try {
    const res = await fetch('/api/retrievers/');
    const configs = await res.json();

    if (!configs || configs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">No retriever configurations registered yet. Click "Register New Retriever Config" or "Load Demo Data".</td></tr>';
      return;
    }

    const rows = await Promise.all(configs.map(async (c) => {
      // Fetch associated metrics for config @ current K
      let recall = 0, precision = 0, mrr = 0, hitRate = 0;
      try {
        const mRes = await fetch(`/api/metrics/?retriever_id=${c.id}&k=${currentK}`);
        if (mRes.ok) {
          const mData = await mRes.json();
          recall = mData.mean_recall;
          precision = mData.mean_precision;
          mrr = mData.mrr;
          hitRate = mData.hit_rate;
        }
      } catch (e) {}

      return `
        <tr>
          <td>
            <div class="fw-bold text-white">${c.name}</div>
            <div class="text-muted small">${c.description || ''}</div>
          </td>
          <td><span class="badge bg-secondary font-monospace">${c.embedding_model}</span></td>
          <td class="fw-bold text-white">${c.chunk_size} tokens</td>
          <td class="text-secondary">${c.chunk_overlap} tokens</td>
          <td class="fw-bold text-success">${recall.toFixed(4)}</td>
          <td class="fw-bold text-info">${precision.toFixed(4)}</td>
          <td class="fw-bold text-warning">${mrr.toFixed(4)}</td>
          <td class="fw-bold text-white">${hitRate}%</td>
          <td class="text-muted small">${new Date(c.created_at).toLocaleDateString()}</td>
        </tr>
      `;
    }));

    tbody.innerHTML = rows.join('');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-danger">Error loading chunking configurations.</td></tr>';
  }
}

async function handleNewConfigSubmit(e) {
  e.preventDefault();

  const name = document.getElementById('cfgName').value.trim();
  const model = document.getElementById('cfgModel').value.trim();
  const size = parseInt(document.getElementById('cfgSize').value);
  const overlap = parseInt(document.getElementById('cfgOverlap').value);
  const topK = parseInt(document.getElementById('cfgTopK').value);
  const desc = document.getElementById('cfgDesc').value.trim();

  try {
    const res = await fetch('/api/retrievers/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        name: name,
        embedding_model: model,
        chunk_size: size,
        chunk_overlap: overlap,
        top_k: topK,
        description: desc
      })
    });

    if (res.ok) {
      showToast(`Retriever configuration '${name}' registered!`, 'success');
      const modalEl = document.getElementById('newConfigModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();
      document.getElementById('newConfigForm').reset();
      loadChunkingAnalysisTable();
    } else {
      showToast('Failed to register configuration', 'error');
    }
  } catch (err) {
    showToast('Error sending configuration data', 'error');
  }
}
