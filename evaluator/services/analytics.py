from typing import Dict, Any, Optional
from django.db.models import Avg, Count, Q
from evaluator.models import Dataset, EvaluationQuestion, EvaluationResult, RetrieverConfig

def get_dashboard_analytics(dataset_id: Optional[int] = None, k: int = 5, retriever_config_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get aggregated metrics and chart distributions for dashboard and analytics views.
    """
    results_qs = EvaluationResult.objects.filter(k=k)
    
    if dataset_id:
        results_qs = results_qs.filter(evaluation_question__dataset_id=dataset_id)
    if retriever_config_id:
        results_qs = results_qs.filter(evaluation_question__retriever_config_id=retriever_config_id)

    total_questions = results_qs.count()

    if total_questions == 0:
        return {
            'k': k,
            'dataset_id': dataset_id,
            'retriever_config_id': retriever_config_id,
            'total_questions': 0,
            'mean_recall': 0.0,
            'mean_precision': 0.0,
            'hit_rate': 0.0,
            'mrr': 0.0,
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'performance_by_k': [],
            'hit_vs_miss': {'hits': 0, 'misses': 0},
            'recall_distribution': {'labels': [], 'counts': []},
            'precision_distribution': {'labels': [], 'counts': []},
            'mrr_distribution': {'labels': [], 'counts': []},
            'rank_distribution': {'labels': [], 'counts': []},
            'lowest_performing_questions': []
        }

    aggs = results_qs.aggregate(
        mean_recall=Avg('recall'),
        mean_precision=Avg('precision'),
        mean_mrr=Avg('reciprocal_rank'),
        hits_count=Count('id', filter=Q(hit=True)),
        misses_count=Count('id', filter=Q(hit=False))
    )

    mean_recall = round(aggs['mean_recall'] or 0.0, 4)
    mean_precision = round(aggs['mean_precision'] or 0.0, 4)
    mrr = round(aggs['mean_mrr'] or 0.0, 4)
    successful_retrievals = aggs['hits_count'] or 0
    failed_retrievals = aggs['misses_count'] or 0
    hit_rate = round((successful_retrievals / total_questions) * 100, 2) if total_questions > 0 else 0.0

    # Performance across K values (1, 3, 5, 10)
    performance_by_k = []
    k_options = [1, 3, 5, 10]
    for k_val in k_options:
        k_qs = EvaluationResult.objects.filter(k=k_val)
        if dataset_id:
            k_qs = k_qs.filter(evaluation_question__dataset_id=dataset_id)
        if retriever_config_id:
            k_qs = k_qs.filter(evaluation_question__retriever_config_id=retriever_config_id)
        
        k_count = k_qs.count()
        if k_count > 0:
            k_aggs = k_qs.aggregate(
                rec=Avg('recall'),
                prec=Avg('precision'),
                mrr_val=Avg('reciprocal_rank'),
                hits=Count('id', filter=Q(hit=True))
            )
            performance_by_k.append({
                'k': k_val,
                'recall': round(k_aggs['rec'] or 0.0, 4),
                'precision': round(k_aggs['prec'] or 0.0, 4),
                'mrr': round(k_aggs['mrr_val'] or 0.0, 4),
                'hit_rate': round(((k_aggs['hits'] or 0) / k_count) * 100, 2)
            })

    # Metric distributions (buckets)
    recall_buckets = {'0.0': 0, '0.01-0.25': 0, '0.26-0.50': 0, '0.51-0.75': 0, '0.76-0.99': 0, '1.0': 0}
    precision_buckets = {'0.0': 0, '0.01-0.25': 0, '0.26-0.50': 0, '0.51-0.75': 0, '0.76-0.99': 0, '1.0': 0}
    mrr_buckets = {'0.0 (Miss)': 0, '0.1-0.33 (Rank 3+)': 0, '0.5 (Rank 2)': 0, '1.0 (Rank 1)': 0}
    rank_buckets = {'Rank 1': 0, 'Rank 2': 0, 'Rank 3': 0, 'Rank 4-5': 0, 'Rank 6-10': 0, 'Not in Top K': 0}

    for res in results_qs.select_related('evaluation_question'):
        # Recall bucket
        r = res.recall
        if r == 0.0:
            recall_buckets['0.0'] += 1
        elif r == 1.0:
            recall_buckets['1.0'] += 1
        elif r <= 0.25:
            recall_buckets['0.01-0.25'] += 1
        elif r <= 0.50:
            recall_buckets['0.26-0.50'] += 1
        elif r <= 0.75:
            recall_buckets['0.51-0.75'] += 1
        else:
            recall_buckets['0.76-0.99'] += 1

        # Precision bucket
        p = res.precision
        if p == 0.0:
            precision_buckets['0.0'] += 1
        elif p == 1.0:
            precision_buckets['1.0'] += 1
        elif p <= 0.25:
            precision_buckets['0.01-0.25'] += 1
        elif p <= 0.50:
            precision_buckets['0.26-0.50'] += 1
        elif p <= 0.75:
            precision_buckets['0.51-0.75'] += 1
        else:
            precision_buckets['0.76-0.99'] += 1

        # MRR bucket
        rr = res.reciprocal_rank
        if rr == 0.0:
            mrr_buckets['0.0 (Miss)'] += 1
        elif rr == 1.0:
            mrr_buckets['1.0 (Rank 1)'] += 1
        elif rr == 0.5:
            mrr_buckets['0.5 (Rank 2)'] += 1
        else:
            mrr_buckets['0.1-0.33 (Rank 3+)'] += 1

        # Rank distribution
        frr = res.first_relevant_rank
        if res.hit and frr is not None:
            if frr == 1:
                rank_buckets['Rank 1'] += 1
            elif frr == 2:
                rank_buckets['Rank 2'] += 1
            elif frr == 3:
                rank_buckets['Rank 3'] += 1
            elif frr <= 5:
                rank_buckets['Rank 4-5'] += 1
            elif frr <= 10:
                rank_buckets['Rank 6-10'] += 1
            else:
                rank_buckets['Not in Top K'] += 1
        else:
            rank_buckets['Not in Top K'] += 1

    # Lowest performing questions
    lowest_questions_qs = results_qs.select_related('evaluation_question', 'evaluation_question__dataset').order_by('recall', 'precision', 'hit')[:10]
    lowest_performing_questions = [
        {
            'id': res.evaluation_question.id,
            'question': res.evaluation_question.question,
            'dataset': res.evaluation_question.dataset.name,
            'recall': res.recall,
            'precision': res.precision,
            'hit': res.hit,
            'reciprocal_rank': res.reciprocal_rank,
            'first_relevant_rank': res.first_relevant_rank
        }
        for res in lowest_questions_qs
    ]

    return {
        'k': k,
        'dataset_id': dataset_id,
        'retriever_config_id': retriever_config_id,
        'total_questions': total_questions,
        'mean_recall': mean_recall,
        'mean_precision': mean_precision,
        'hit_rate': hit_rate,
        'mrr': mrr,
        'successful_retrievals': successful_retrievals,
        'failed_retrievals': failed_retrievals,
        'performance_by_k': performance_by_k,
        'hit_vs_miss': {
            'hits': successful_retrievals,
            'misses': failed_retrievals
        },
        'recall_distribution': {
            'labels': list(recall_buckets.keys()),
            'counts': list(recall_buckets.values())
        },
        'precision_distribution': {
            'labels': list(precision_buckets.keys()),
            'counts': list(precision_buckets.values())
        },
        'mrr_distribution': {
            'labels': list(mrr_buckets.keys()),
            'counts': list(mrr_buckets.values())
        },
        'rank_distribution': {
            'labels': list(rank_buckets.keys()),
            'counts': list(rank_buckets.values())
        },
        'lowest_performing_questions': lowest_performing_questions
    }


def compare_retrievers(config_a_id: int, config_b_id: int, k: int = 5) -> Dict[str, Any]:
    """
    Compare performance between two RetrieverConfigs side-by-side.
    """
    try:
        config_a = RetrieverConfig.objects.get(id=config_a_id)
        config_b = RetrieverConfig.objects.get(id=config_b_id)
    except RetrieverConfig.DoesNotExist:
        return {'error': 'One or both retriever configurations not found.'}

    metrics_a = get_dashboard_analytics(k=k, retriever_config_id=config_a_id)
    metrics_b = get_dashboard_analytics(k=k, retriever_config_id=config_b_id)

    # Question level differences
    questions_a = {r['id']: r for r in metrics_a.get('lowest_performing_questions', [])}
    
    return {
        'k': k,
        'config_a': {
            'id': config_a.id,
            'name': config_a.name,
            'embedding_model': config_a.embedding_model,
            'chunk_size': config_a.chunk_size,
            'chunk_overlap': config_a.chunk_overlap,
            'top_k': config_a.top_k,
            'metrics': {
                'recall': metrics_a['mean_recall'],
                'precision': metrics_a['mean_precision'],
                'hit_rate': metrics_a['hit_rate'],
                'mrr': metrics_a['mrr'],
                'total_questions': metrics_a['total_questions']
            }
        },
        'config_b': {
            'id': config_b.id,
            'name': config_b.name,
            'embedding_model': config_b.embedding_model,
            'chunk_size': config_b.chunk_size,
            'chunk_overlap': config_b.chunk_overlap,
            'top_k': config_b.top_k,
            'metrics': {
                'recall': metrics_b['mean_recall'],
                'precision': metrics_b['mean_precision'],
                'hit_rate': metrics_b['hit_rate'],
                'mrr': metrics_b['mrr'],
                'total_questions': metrics_b['total_questions']
            }
        },
        'differences': {
            'recall_diff': round(metrics_b['mean_recall'] - metrics_a['mean_recall'], 4),
            'precision_diff': round(metrics_b['mean_precision'] - metrics_a['mean_precision'], 4),
            'hit_rate_diff': round(metrics_b['hit_rate'] - metrics_a['hit_rate'], 2),
            'mrr_diff': round(metrics_b['mrr'] - metrics_a['mrr'], 4)
        }
    }
