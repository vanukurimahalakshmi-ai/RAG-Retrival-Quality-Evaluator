let currentK = 5;

document.addEventListener('DOMContentLoaded', () => {
  fetchQuestionDetail();

  window.addEventListener('k-changed', (e) => {
    currentK = e.detail.k;
    document.getElementById('kBadge').textContent = `K=${currentK}`;
    fetchQuestionDetail();
  });
});

async function fetchQuestionDetail() {
  try {
    const res = await fetch(`/api/evaluations/${QUESTION_ID}/?k=${currentK}`);
    if (!res.ok) {
      showToast('Question not found', 'error');
      return;
    }
    const data = await res.json();
    renderQuestionDetail(data);
  } catch (err) {
    console.error('Error fetching question detail:', err);
  }
}

function renderQuestionDetail(data) {
  document.getElementById('qIdBadge').textContent = `#${data.id}`;
  document.getElementById('qDatasetName').textContent = data.dataset_name;
  document.getElementById('qTextDisplay').textContent = data.question;

  // Render Expected Chunks
  const expContainer = document.getElementById('expectedChunksList');
  if (data.expected_chunks && data.expected_chunks.length > 0) {
    expContainer.innerHTML = data.expected_chunks.map(c => `
      <span class="badge bg-success text-white py-2 px-3 font-monospace fs-6">
        <i class="bi bi-check2-circle me-1"></i> ${c}
      </span>
    `).join('');
  } else {
    expContainer.innerHTML = '<span class="text-muted">No ground truth expected chunks specified.</span>';
  }

  // Render Ranked Retrieved Chunks
  const container = document.getElementById('rankedChunksContainer');
  if (!data.ranked_retrieved_chunks || data.ranked_retrieved_chunks.length === 0) {
    container.innerHTML = '<div class="text-center py-4 text-muted">No chunks were retrieved.</div>';
  } else {
    container.innerHTML = data.ranked_retrieved_chunks.map(item => `
      <div class="chunk-rank-item ${item.is_relevant ? 'relevant' : 'irrelevant'}">
        <div class="d-flex align-items-center gap-3">
          <span class="rank-badge">Rank ${item.rank}</span>
          <span class="font-monospace fw-bold fs-6 ${item.is_relevant ? 'text-success' : 'text-secondary'}">${item.chunk}</span>
        </div>
        <div>
          ${item.is_relevant ? 
            '<span class="badge-hit"><i class="bi bi-check-circle-fill"></i> Relevant Chunk</span>' : 
            '<span class="badge-miss"><i class="bi bi-x-circle-fill"></i> Irrelevant Chunk</span>'
          }
        </div>
      </div>
    `).join('');
  }

  // Render Metrics @ K
  const resultAtK = (data.results || []).find(r => r.k === currentK) || {};
  const hit = resultAtK.hit !== undefined ? resultAtK.hit : false;

  document.getElementById('hitBadgeContainer').innerHTML = hit ?
    '<span class="badge-hit fs-6 py-2 px-3"><i class="bi bi-check-circle-fill"></i> Successful Hit</span>' :
    '<span class="badge-miss fs-6 py-2 px-3"><i class="bi bi-x-circle-fill"></i> Retrieval Failure</span>';

  document.getElementById('mRecall').textContent = (resultAtK.recall !== undefined ? resultAtK.recall : 0).toFixed(4);
  document.getElementById('mPrecision').textContent = (resultAtK.precision !== undefined ? resultAtK.precision : 0).toFixed(4);
  document.getElementById('mRR').textContent = (resultAtK.reciprocal_rank !== undefined ? resultAtK.reciprocal_rank : 0).toFixed(4);
  document.getElementById('mFirstRank').textContent = resultAtK.first_relevant_rank ? `Rank ${resultAtK.first_relevant_rank}` : 'Not in Retrieved';
  document.getElementById('mRetrieverName').textContent = data.retriever_name || 'Default';
}
