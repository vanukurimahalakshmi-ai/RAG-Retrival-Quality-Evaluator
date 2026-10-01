"""
pdf_quality.py
==============
Two services:
  1. assess_document_quality(chunks)  → rates a PDF for RAG suitability
  2. search_chunks(query, dataset_id) → keyword search across stored chunks (Q&A)
"""

import re
import math
from collections import Counter
from typing import List, Dict, Any


# ─────────────────────────────────────────────
# 1.  DOCUMENT QUALITY ASSESSMENT
# ─────────────────────────────────────────────

def assess_document_quality(chunks: List[Dict[str, Any]], total_pages: int) -> Dict[str, Any]:
    """
    Analyses extracted chunks and returns a quality report:
    {
        score: 0-100,
        rating: 'Excellent' | 'Good' | 'Average' | 'Poor',
        rating_color: 'success' | 'primary' | 'warning' | 'danger',
        checks: [ { label, passed, detail } ],
        summary: str,
        recommendations: [ str ],
    }
    """
    checks = []
    total_score = 0
    recommendations = []

    if not chunks:
        return {
            'score': 0,
            'rating': 'Poor',
            'rating_color': 'danger',
            'checks': [{'label': 'Text extraction', 'passed': False, 'detail': 'No chunks could be extracted.'}],
            'summary': 'No readable text was found. The PDF may be scanned or image-only.',
            'recommendations': ['Use an OCR tool (e.g. Adobe Acrobat, Tesseract) to convert scanned PDFs to searchable text before uploading.'],
        }

    # ── Check 1: Sufficient content volume ──────────────────────────────
    total_words = sum(c.get('word_count', len(c.get('content', '').split())) for c in chunks)
    has_enough_words = total_words >= 300
    checks.append({
        'label': 'Content volume',
        'passed': has_enough_words,
        'detail': f'{total_words:,} total words across {len(chunks)} chunks' +
                  ('' if has_enough_words else ' — very low; document may be too short for meaningful RAG evaluation')
    })
    if has_enough_words:
        total_score += 25
    else:
        recommendations.append('Add more content. RAG evaluation works best with documents that have at least a few hundred words per topic.')

    # ── Check 2: Average chunk word count in healthy range ──────────────
    avg_words = total_words / max(len(chunks), 1)
    healthy_avg = 50 <= avg_words <= 400
    checks.append({
        'label': 'Chunk size balance',
        'passed': healthy_avg,
        'detail': f'Average {avg_words:.0f} words/chunk (ideal: 50–400 words)' +
                  ('' if healthy_avg else ' — chunks are too short or too long, which can hurt retrieval precision')
    })
    if healthy_avg:
        total_score += 20
    elif avg_words < 50:
        recommendations.append('Consider using a larger chunk size (more words per chunk) to capture richer context.')
    else:
        recommendations.append('Consider reducing chunk size so each chunk is more focused and retrievable.')

    # ── Check 3: Text diversity / not repetitive ────────────────────────
    all_text = ' '.join(c.get('content', '') for c in chunks).lower()
    words_in_doc = re.findall(r'\b[a-z]{3,}\b', all_text)
    unique_ratio = len(set(words_in_doc)) / max(len(words_in_doc), 1)
    is_diverse = unique_ratio >= 0.2
    checks.append({
        'label': 'Vocabulary diversity',
        'passed': is_diverse,
        'detail': f'{unique_ratio * 100:.1f}% unique word ratio (ideal ≥ 20%)' +
                  ('' if is_diverse else ' — highly repetitive text will yield low-quality retrieval')
    })
    if is_diverse:
        total_score += 20
    else:
        recommendations.append('The document appears repetitive. Consider curating the source material for better retrieval quality.')

    # ── Check 4: Structural quality (sentence boundaries) ──────────────
    sentence_count = len(re.findall(r'[.!?]+', all_text))
    good_structure = sentence_count >= max(5, len(chunks) * 2)
    checks.append({
        'label': 'Sentence structure',
        'passed': good_structure,
        'detail': f'~{sentence_count} sentence boundaries detected' +
                  ('' if good_structure else ' — text may lack proper punctuation or be mostly headings/tables')
    })
    if good_structure:
        total_score += 20
    else:
        recommendations.append('Ensure the document contains well-formed sentences. Tables and headers without body text are poor RAG material.')

    # ── Check 5: Multi-page coverage ────────────────────────────────────
    pages_with_content = len(set(c.get('page', 1) for c in chunks))
    good_coverage = pages_with_content >= min(total_pages, 2)
    checks.append({
        'label': 'Page coverage',
        'passed': good_coverage,
        'detail': f'Text found on {pages_with_content}/{total_pages} pages' +
                  ('' if good_coverage else ' — most pages appear empty or image-only')
    })
    if good_coverage:
        total_score += 15
    else:
        recommendations.append('Many pages appear to contain no extractable text. Ensure the PDF is not primarily composed of images or scanned pages.')

    # ── Rating label ─────────────────────────────────────────────────────
    if total_score >= 85:
        rating, color = 'Excellent', 'success'
        summary = 'This document is well-structured, content-rich, and highly suitable for RAG retrieval evaluation.'
    elif total_score >= 65:
        rating, color = 'Good', 'primary'
        summary = 'This document is a good RAG candidate with minor areas for improvement.'
    elif total_score >= 40:
        rating, color = 'Average', 'warning'
        summary = 'This document can be used for RAG evaluation but may produce inconsistent retrieval quality.'
    else:
        rating, color = 'Poor', 'danger'
        summary = 'This document is not well-suited for RAG evaluation. See the recommendations below.'

    return {
        'score': total_score,
        'rating': rating,
        'rating_color': color,
        'checks': checks,
        'summary': summary,
        'recommendations': recommendations,
    }


# ─────────────────────────────────────────────
# 2.  CHUNK Q&A — KEYWORD SEARCH
# ─────────────────────────────────────────────

_STOPWORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'is','it','this','that','was','are','be','as','by','from','has','have',
    'had','not','do','does','did','what','which','who','when','where','how',
    'can','will','would','could','should','may','might','more','than','then',
    'its','about','also','their','there','them','they','been','some','into',
    'up','out','so','if','we','you','i','he','she','his','her','our','my',
    'your','were','all','any','each','one','two','per','both','while',
}


def _tokenise(text: str) -> List[str]:
    return [w for w in re.findall(r'\b[a-z]{3,}\b', text.lower()) if w not in _STOPWORDS]


def _tfidf_score(query_tokens: List[str], chunk_tokens: List[str], idf: Dict[str, float]) -> float:
    """Simple TF-IDF dot product between query and chunk."""
    chunk_freq = Counter(chunk_tokens)
    chunk_len = max(len(chunk_tokens), 1)
    score = 0.0
    for qt in query_tokens:
        tf = chunk_freq.get(qt, 0) / chunk_len
        score += tf * idf.get(qt, 0)
    return score


def search_chunks(query: str, dataset_id: int, top_k: int = 5) -> Dict[str, Any]:
    """
    Keyword/TF-IDF search across DocumentChunk records for a given dataset.
    Returns top_k matching chunks with relevance scores and highlights.
    """
    from evaluator.models import DocumentChunk  # local import to avoid circular deps

    chunks_qs = DocumentChunk.objects.filter(dataset_id=dataset_id).values(
        'id', 'chunk_id', 'page', 'chunk_index', 'content', 'word_count'
    )
    chunks = list(chunks_qs)

    if not chunks:
        return {
            'query': query,
            'results': [],
            'total_searched': 0,
            'message': 'No stored chunks found for this dataset. Re-upload the PDF to enable Q&A.'
        }

    query_tokens = _tokenise(query)
    if not query_tokens:
        return {'query': query, 'results': [], 'total_searched': len(chunks), 'message': 'Query is too short or contains only common words.'}

    # ── Build IDF across all chunks ──────────────────────────────────────
    N = len(chunks)
    df: Counter = Counter()
    tokenised_chunks = []
    for ch in chunks:
        toks = _tokenise(ch['content'])
        tokenised_chunks.append(toks)
        df.update(set(toks))

    idf = {term: math.log((N + 1) / (df[term] + 1)) + 1 for term in df}

    # ── Score each chunk ─────────────────────────────────────────────────
    scored = []
    for ch, toks in zip(chunks, tokenised_chunks):
        score = _tfidf_score(query_tokens, toks, idf)
        if score > 0:
            scored.append((score, ch))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # ── Build results with highlighted snippets ──────────────────────────
    results = []
    for rank, (score, ch) in enumerate(top, start=1):
        snippet = _highlight_snippet(ch['content'], query_tokens, window=50)
        results.append({
            'rank': rank,
            'chunk_id': ch['chunk_id'],
            'page': ch['page'],
            'score': round(score, 4),
            'relevance_pct': min(100, round(score * 300)),   # rough 0-100 display scale
            'snippet': snippet,
            'word_count': ch['word_count'],
        })

    # ── Generate an answer summary (extractive: first most-relevant sentence) ─
    answer = _extract_answer(query_tokens, top)

    return {
        'query': query,
        'answer': answer,
        'results': results,
        'total_searched': N,
        'message': f'Found {len(results)} relevant chunk(s) from {N} total chunks.'
    }


def _highlight_snippet(text: str, query_tokens: List[str], window: int = 50) -> str:
    """Return a ≤2*window word snippet centred on the first query token hit."""
    words = text.split()
    best_idx = -1
    for i, w in enumerate(words):
        if re.sub(r'[^a-z]', '', w.lower()) in query_tokens:
            best_idx = i
            break
    if best_idx == -1:
        # No direct hit — return start of chunk
        return ' '.join(words[:window]) + ('…' if len(words) > window else '')
    start = max(0, best_idx - window // 2)
    end = min(len(words), start + window)
    snippet_words = words[start:end]
    return ('…' if start > 0 else '') + ' '.join(snippet_words) + ('…' if end < len(words) else '')


def _extract_answer(query_tokens: List[str], top_chunks) -> str:
    """Extractive answer: find the best sentence in top chunks that contains query terms."""
    if not top_chunks:
        return 'No relevant content was found for your question.'
    _, best_chunk = top_chunks[0]
    content = best_chunk['content']
    sentences = re.split(r'(?<=[.!?])\s+', content)
    best_sent = ''
    best_hits = 0
    for sent in sentences:
        toks = set(_tokenise(sent))
        hits = len(toks & set(query_tokens))
        if hits > best_hits:
            best_hits = hits
            best_sent = sent
    if not best_sent:
        best_sent = sentences[0] if sentences else content[:200]
    return best_sent.strip()
