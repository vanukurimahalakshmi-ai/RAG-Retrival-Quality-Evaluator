from typing import List, Dict, Any, Optional

def calculate_metrics(expected_chunks: List[str], retrieved_chunks: List[str], k: int = 5) -> Dict[str, Any]:
    """
    Calculate RAG evaluation metrics for a single question given expected and retrieved chunks at cut-off K.

    Metrics:
    - Recall@K: proportion of expected/relevant chunks in top K retrieved chunks.
    - Precision@K: proportion of top K retrieved chunks that are relevant.
    - Hit: True if at least 1 expected chunk is in top K retrieved chunks.
    - First Relevant Rank: 1-based rank of first expected chunk in retrieved_chunks (or None if not found).
    - Reciprocal Rank: 1 / first_relevant_rank if first_relevant_rank <= K else 0.0.
    """
    if k <= 0:
        k = 5

    # Normalize chunk identifiers (strip whitespace)
    expected_set = set(str(c).strip() for c in expected_chunks if str(c).strip())
    retrieved_list = [str(c).strip() for c in retrieved_chunks if str(c).strip()]
    top_k_retrieved = retrieved_list[:k]

    if not expected_set:
        return {
            'recall': 0.0,
            'precision': 0.0,
            'hit': False,
            'reciprocal_rank': 0.0,
            'first_relevant_rank': None,
            'k': k
        }

    # Find first relevant rank in all retrieved chunks
    first_relevant_rank: Optional[int] = None
    for idx, chunk in enumerate(retrieved_list, start=1):
        if chunk in expected_set:
            first_relevant_rank = idx
            break

    # Calculate top-K intersections
    top_k_set = set(top_k_retrieved)
    relevant_retrieved_in_k = expected_set.intersection(top_k_set)
    num_relevant_in_k = len(relevant_retrieved_in_k)

    # Recall@K = |relevant in K| / |expected|
    recall = num_relevant_in_k / len(expected_set) if expected_set else 0.0

    # Precision@K = |relevant in K| / K
    precision = num_relevant_in_k / k if k > 0 else 0.0

    # Hit@K = True if at least 1 relevant chunk in top K
    hit = num_relevant_in_k > 0

    # Reciprocal Rank @ K
    if first_relevant_rank is not None and first_relevant_rank <= k:
        reciprocal_rank = 1.0 / first_relevant_rank
    else:
        reciprocal_rank = 0.0

    return {
        'recall': round(recall, 4),
        'precision': round(precision, 4),
        'hit': hit,
        'reciprocal_rank': round(reciprocal_rank, 4),
        'first_relevant_rank': first_relevant_rank,
        'k': k
    }


def evaluate_question(question_obj, k_values: Optional[List[int]] = None):
    """
    Evaluate an EvaluationQuestion instance across specified K values and store EvaluationResult objects.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    from evaluator.models import EvaluationResult

    results = []
    for k in k_values:
        metrics = calculate_metrics(
            expected_chunks=question_obj.expected_chunks,
            retrieved_chunks=question_obj.retrieved_chunks,
            k=k
        )
        result_obj, _ = EvaluationResult.objects.update_or_create(
            evaluation_question=question_obj,
            k=k,
            defaults={
                'recall': metrics['recall'],
                'precision': metrics['precision'],
                'hit': metrics['hit'],
                'reciprocal_rank': metrics['reciprocal_rank'],
                'first_relevant_rank': metrics['first_relevant_rank'],
            }
        )
        results.append(result_obj)
    return results


def evaluate_dataset(dataset_obj, k_values: Optional[List[int]] = None):
    """
    Evaluate all EvaluationQuestions in a Dataset across specified K values.
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]

    results = []
    for question in dataset_obj.questions.all():
        q_results = evaluate_question(question, k_values=k_values)
        results.extend(q_results)
    return results
