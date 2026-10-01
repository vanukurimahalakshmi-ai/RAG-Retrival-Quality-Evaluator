import csv
import json
from io import StringIO
from typing import Optional, Tuple
from evaluator.models import EvaluationResult

def export_results_csv(dataset_id: Optional[int] = None, k: int = 5) -> str:
    """
    Generate CSV string of evaluation results.
    """
    qs = EvaluationResult.objects.filter(k=k).select_related('evaluation_question')
    if dataset_id:
        qs = qs.filter(evaluation_question__dataset_id=dataset_id)

    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Question ID',
        'Question',
        'Expected Chunks',
        'Retrieved Chunks',
        'K',
        'Recall@K',
        'Precision@K',
        'Hit Rate',
        'Reciprocal Rank',
        'First Relevant Rank'
    ])

    for res in qs:
        q = res.evaluation_question
        writer.writerow([
            q.id,
            q.question,
            json.dumps(q.expected_chunks),
            json.dumps(q.retrieved_chunks),
            res.k,
            res.recall,
            res.precision,
            res.hit,
            res.reciprocal_rank,
            res.first_relevant_rank if res.first_relevant_rank is not None else ''
        ])

    return output.getvalue()


def export_results_json(dataset_id: Optional[int] = None, k: int = 5) -> str:
    """
    Generate formatted JSON string of evaluation results.
    """
    qs = EvaluationResult.objects.filter(k=k).select_related('evaluation_question')
    if dataset_id:
        qs = qs.filter(evaluation_question__dataset_id=dataset_id)

    results_data = []
    for res in qs:
        q = res.evaluation_question
        results_data.append({
            'question_id': q.id,
            'question': q.question,
            'expected_chunks': q.expected_chunks,
            'retrieved_chunks': q.retrieved_chunks,
            'k': res.k,
            'recall': res.recall,
            'precision': res.precision,
            'hit': res.hit,
            'reciprocal_rank': res.reciprocal_rank,
            'first_relevant_rank': res.first_relevant_rank
        })

    return json.dumps({
        'k': k,
        'dataset_id': dataset_id,
        'total_results': len(results_data),
        'evaluations': results_data
    }, indent=2)
