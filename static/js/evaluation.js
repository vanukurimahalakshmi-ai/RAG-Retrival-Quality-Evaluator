let currentPage = 1;
let currentK = 5;

document.addEventListener('DOMContentLoaded', () => {
  // Check URL params if coming from datasets page or dashboard
  const urlParams = new URLSearchParams(window.location.search);
  const datasetParam = urlParams.get('dataset_id');

  loadDatasetFilterOptions(datasetParam);
  fetchEvaluationTable();

  // Input listeners
  document.getElementById('searchInput').addEventListener('input', debounce(() => { currentPage = 1; fetchEvaluationTable(); }, 300));
  document.getElementById('datasetFilterSel').addEventListener('change', () => { currentPage = 1; fetchEvaluationTable(); });
  document.getElementById('hitFilterSel').addEventListener('change', () => { currentPage = 1; fetchEvaluationTable(); });
  document.getElementById('sortSel').addEventListener('change', () => { currentPage = 1; fetchEvaluationTable(); });

  document.getElementById('btnResetFilters').addEventListener('click', () => {
    document.getElementById('searchInput').value = '';
    document.getElementById('datasetFilterSel').value = '';
    document.getElementById('hitFilterSel').value = '';
    document.getElementById('sortSel').value = '-id';
    currentPage = 1;
    fetchEvaluationTable();
  });

  document.getElementById('btnPrevPage').addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      fetchEvaluationTable();
    }
  });

  document.getElementById('btnNextPage').addEventListener('click', () => {
    currentPage++;
    fetchEvaluationTable();
  });

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.querySelectorAll('.k-label').forEach(el => el.textContent = currentK);
    currentPage = 1;
    fetchEvaluationTable();
  });
});

async function loadDatasetFilterOptions(selectedId) {
  try {
    const res = await fetch('/api/datasets/');
    const datasets = await res.json();
    const select = document.getElementById('datasetFilterSel');
    select.innerHTML = '<option value="">All Datasets</option>';
    datasets.forEach(d => {
      const selected = selectedId && parseInt(selectedId) === d.id ? 'selected' : '';
      select.innerHTML += `<option value="${d.id}" ${selected}>${d.name}</option>`;
    });
  } catch (err) {
    console.error('Failed to load datasets filter', err);
  }
}

async function fetchEvaluationTable() {
  const tbody = document.getElementById('evaluationTableBody');
  const search = document.getElementById('searchInput').value.trim();
  const datasetId = document.getElementById('datasetFilterSel').value;
  const hit = document.getElementById('hitFilterSel').value;
  const ordering = document.getElementById('sortSel').value;

  let url = `/api/evaluations/?k=${currentK}&page=${currentPage}&page_size=10&ordering=${ordering}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (datasetId) url += `&dataset_id=${datasetId}`;
  if (hit !== '') url += `&hit=${hit}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (!data.results || data.results.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">No matching evaluation records found.</td></tr>';
      updatePaginationControls(0, 1, 1);
      return;
    }

    tbody.innerHTML = data.results.map(r => {
      const expBadges = r.expected_chunks.map(c => `<span class="badge-tag me-1">${c}</span>`).join('');
      const retTopK = r.retrieved_chunks.slice(0, currentK);
      const expectedSet = new Set(r.expected_chunks.map(c => String(c).trim()));
      
      const retBadges = retTopK.map(c => {
        const isRel = expectedSet.has(String(c).trim());
        return `<span class="badge ${isRel ? 'bg-success' : 'bg-dark text-secondary'} border border-secondary me-1" title="${isRel ? 'Relevant Chunk' : 'Irrelevant Chunk'}">${c}</span>`;
      }).join('');

      return `
        <tr class="align-middle" style="cursor: pointer;" onclick="window.location.href='/questions/${r.id}/'">
          <td><span class="badge-tag">#${r.id}</span></td>
          <td>
            <a href="/questions/${r.id}/" class="text-white text-decoration-none fw-medium hover-blue" onclick="event.stopPropagation();">
              ${r.question}
            </a>
            <div class="text-muted small">${r.dataset_name}</div>
          </td>
          <td><div class="d-flex flex-wrap gap-1">${expBadges}</div></td>
          <td><div class="d-flex flex-wrap gap-1">${retBadges}</div></td>
          <td>
            ${r.hit ? '<span class="badge-hit"><i class="bi bi-check-circle"></i> Hit</span>' : '<span class="badge-miss"><i class="bi bi-x-circle"></i> Miss</span>'}
          </td>
          <td class="fw-bold ${r.recall > 0.5 ? 'text-success' : 'text-danger'}">${r.recall.toFixed(2)}</td>
          <td class="fw-bold text-info">${r.precision.toFixed(2)}</td>
          <td class="fw-bold text-warning">${r.reciprocal_rank.toFixed(2)}</td>
          <td>${r.first_relevant_rank ? `Rank ${r.first_relevant_rank}` : '<span class="text-muted">N/A</span>'}</td>
          <td>
            <a href="/questions/${r.id}/" class="btn-secondary-custom btn-sm py-1 px-2" onclick="event.stopPropagation();">
              Inspect <i class="bi bi-arrow-right-short"></i>
            </a>
          </td>
        </tr>
      `;
    }).join('');

    updatePaginationControls(data.count, data.page, data.total_pages);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-danger">Error loading evaluation data.</td></tr>';
  }
}

function updatePaginationControls(total, page, totalPages) {
  document.getElementById('paginationInfo').textContent = `Showing ${total > 0 ? (page - 1) * 10 + 1 : 0} to ${Math.min(page * 10, total)} of ${total} results`;
  document.getElementById('pageIndicator').textContent = `Page ${page} of ${totalPages}`;
  document.getElementById('btnPrevPage').disabled = page <= 1;
  document.getElementById('btnNextPage').disabled = page >= totalPages;
}

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
