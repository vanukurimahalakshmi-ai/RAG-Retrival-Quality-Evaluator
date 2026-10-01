document.addEventListener('DOMContentLoaded', () => {
  loadDatasetsTable();
  loadRetrieverOptions();

  const form = document.getElementById('uploadDatasetForm');
  if (form) {
    form.addEventListener('submit', handleDatasetUpload);
  }

  const demoBtn = document.getElementById('btnLoadDemoSection');
  if (demoBtn) {
    demoBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/datasets/load-demo/', {
          method: 'POST',
          headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (res.ok) {
          showToast(data.message, 'success');
          loadDatasetsTable();
        } else {
          showToast(data.error || 'Failed to load demo data', 'error');
        }
      } catch (err) {
        showToast('Error connecting to server', 'error');
      }
    });
  }
});

async function loadRetrieverOptions() {
  try {
    const res = await fetch('/api/retrievers/');
    if (!res.ok) return;
    const configs = await res.json();
    const select = document.getElementById('retrieverSelect');
    if (!select) return;

    select.innerHTML = '<option value="">Default / Unspecified Retriever</option>';
    configs.forEach(c => {
      select.innerHTML += `<option value="${c.id}">${c.name} (${c.embedding_model})</option>`;
    });
  } catch (err) {
    console.error('Failed to load retrievers', err);
  }
}

async function loadDatasetsTable() {
  const tbody = document.getElementById('datasetsTableBody');
  try {
    const res = await fetch('/api/datasets/');
    const datasets = await res.json();

    if (!datasets || datasets.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">No datasets uploaded yet. Click "Upload New Dataset" or "Load Demo Dataset".</td></tr>';
      return;
    }

    tbody.innerHTML = datasets.map(d => `
      <tr>
        <td><span class="badge-tag">#${d.id}</span></td>
        <td class="fw-bold text-white">${d.name}</td>
        <td class="text-secondary small" style="max-width: 280px;">${d.description || 'No description'}</td>
        <td><span class="badge bg-primary rounded-pill">${d.question_count} Qs</span></td>
        <td>
          ${d.is_demo ? '<span class="badge bg-warning text-dark"><i class="bi bi-star-fill"></i> Built-in Demo</span>' : '<span class="badge bg-secondary">Custom Upload</span>'}
        </td>
        <td class="text-muted small">${new Date(d.created_at).toLocaleDateString()}</td>
        <td>
          <div class="d-flex align-items-center gap-2">
            <a href="/evaluation/?dataset_id=${d.id}" class="btn-secondary-custom btn-sm py-1 px-2">
              <i class="bi bi-eye"></i> View Questions
            </a>
            <button onclick="reEvaluateDataset(${d.id})" class="btn-secondary-custom btn-sm py-1 px-2 text-info" title="Re-calculate Metrics">
              <i class="bi bi-arrow-repeat"></i>
            </button>
            <button onclick="deleteDataset(${d.id})" class="btn-secondary-custom btn-sm py-1 px-2 text-danger" title="Delete Dataset">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Error loading datasets from API.</td></tr>';
  }
}

async function handleDatasetUpload(e) {
  e.preventDefault();

  const errAlert = document.getElementById('uploadErrorAlert');
  errAlert.classList.add('d-none');
  errAlert.innerHTML = '';

  const name = document.getElementById('datasetNameInput').value.trim();
  const description = document.getElementById('datasetDescInput').value.trim();
  const retrieverId = document.getElementById('retrieverSelect').value;
  const fileInput = document.getElementById('datasetFileInput');
  const rawJson = document.getElementById('rawJsonInput').value.trim();

  const formData = new FormData();
  formData.append('name', name);
  if (description) formData.append('description', description);
  if (retrieverId) formData.append('retriever_config_id', retrieverId);

  if (fileInput.files.length > 0) {
    formData.append('file', fileInput.files[0]);
  } else if (rawJson) {
    formData.append('raw_json', rawJson);
  } else {
    errAlert.classList.remove('d-none');
    errAlert.textContent = 'Please select a CSV/JSON file to upload or enter raw JSON in the text area.';
    return;
  }

  const submitBtn = document.getElementById('btnSubmitUpload');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Parsing & Evaluating...';

  try {
    const res = await fetch('/api/datasets/upload/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken },
      body: formData
    });

    const data = await res.json();

    if (res.ok) {
      showToast(data.message, 'success');
      // Close modal
      const modalEl = document.getElementById('uploadDatasetModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();
      form.reset();
      loadDatasetsTable();
    } else {
      let errText = 'Validation failed: ';
      if (data.errors) {
        if (typeof data.errors === 'string') {
          errText += data.errors;
        } else if (data.errors.non_field_errors) {
          errText += data.errors.non_field_errors.join(' ');
        } else {
          errText += JSON.stringify(data.errors);
        }
      } else {
        errText += data.detail || 'Unknown error occurred';
      }
      errAlert.classList.remove('d-none');
      errAlert.innerHTML = `<strong>Validation Error:</strong> ${errText}`;
    }
  } catch (err) {
    errAlert.classList.remove('d-none');
    errAlert.textContent = 'Failed to submit dataset upload. Server error.';
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Submit & Run Evaluation';
  }
}

async function reEvaluateDataset(datasetId) {
  try {
    const res = await fetch('/api/evaluations/run/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken, 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, k_values: [1, 3, 5, 10] })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, 'success');
    } else {
      showToast('Re-evaluation failed', 'error');
    }
  } catch (err) {
    showToast('Network error during re-evaluation', 'error');
  }
}

async function deleteDataset(datasetId) {
  if (!confirm('Are you sure you want to delete this dataset and all associated evaluation questions?')) return;

  try {
    const res = await fetch(`/api/datasets/${datasetId}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrftoken }
    });

    if (res.status === 240 || res.status === 204) {
      showToast('Dataset successfully deleted', 'success');
      loadDatasetsTable();
    } else {
      showToast('Failed to delete dataset', 'error');
    }
  } catch (err) {
    showToast('Network error while deleting dataset', 'error');
  }
}
