from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from evaluator.models import Dataset, EvaluationQuestion, EvaluationResult, RetrieverConfig
from evaluator.services.evaluation import calculate_metrics, evaluate_question, evaluate_dataset

class EvaluationEngineTests(TestCase):
    
    def test_case_1_all_relevant_retrieved(self):
        # All expected chunks retrieved in top K
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_1", "chunk_2", "chunk_3"]
        metrics = calculate_metrics(expected, retrieved, k=3)
        self.assertEqual(metrics['recall'], 1.0)
        self.assertEqual(metrics['precision'], round(2/3, 4))
        self.assertTrue(metrics['hit'])
        self.assertEqual(metrics['first_relevant_rank'], 1)
        self.assertEqual(metrics['reciprocal_rank'], 1.0)

    def test_case_2_no_relevant_retrieved(self):
        # Retrieval failure
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_10", "chunk_11", "chunk_12"]
        metrics = calculate_metrics(expected, retrieved, k=3)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['precision'], 0.0)
        self.assertFalse(metrics['hit'])
        self.assertIsNone(metrics['first_relevant_rank'])
        self.assertEqual(metrics['reciprocal_rank'], 0.0)

    def test_case_3_partial_retrieval(self):
        # 1 of 2 expected chunks retrieved
        expected = ["chunk_1", "chunk_2"]
        retrieved = ["chunk_1", "chunk_99", "chunk_100"]
        metrics = calculate_metrics(expected, retrieved, k=3)
        self.assertEqual(metrics['recall'], 0.5)
        self.assertEqual(metrics['precision'], round(1/3, 4))
        self.assertTrue(metrics['hit'])
        self.assertEqual(metrics['first_relevant_rank'], 1)
        self.assertEqual(metrics['reciprocal_rank'], 1.0)

    def test_case_4_relevant_chunk_at_rank_1(self):
        expected = ["chunk_A"]
        retrieved = ["chunk_A", "chunk_B", "chunk_C"]
        metrics = calculate_metrics(expected, retrieved, k=5)
        self.assertEqual(metrics['first_relevant_rank'], 1)
        self.assertEqual(metrics['reciprocal_rank'], 1.0)

    def test_case_5_relevant_chunk_at_rank_3(self):
        expected = ["chunk_X"]
        retrieved = ["chunk_A", "chunk_B", "chunk_X", "chunk_D"]
        metrics = calculate_metrics(expected, retrieved, k=5)
        self.assertEqual(metrics['first_relevant_rank'], 3)
        self.assertEqual(metrics['reciprocal_rank'], round(1/3, 4))

    def test_case_6_multiple_relevant_chunks(self):
        expected = ["chunk_1", "chunk_2", "chunk_3"]
        retrieved = ["chunk_A", "chunk_1", "chunk_2", "chunk_3"]
        metrics = calculate_metrics(expected, retrieved, k=4)
        self.assertEqual(metrics['recall'], 1.0)
        self.assertEqual(metrics['precision'], 0.75)
        self.assertEqual(metrics['first_relevant_rank'], 2)
        self.assertEqual(metrics['reciprocal_rank'], 0.5)

    def test_case_7_k_larger_than_retrieved_count(self):
        expected = ["chunk_1"]
        retrieved = ["chunk_1"]
        metrics = calculate_metrics(expected, retrieved, k=10)
        self.assertEqual(metrics['recall'], 1.0)
        self.assertEqual(metrics['precision'], 0.1) # 1 / 10
        self.assertTrue(metrics['hit'])

    def test_case_8_empty_retrieved_results(self):
        expected = ["chunk_1"]
        retrieved = []
        metrics = calculate_metrics(expected, retrieved, k=5)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['precision'], 0.0)
        self.assertFalse(metrics['hit'])
        self.assertIsNone(metrics['first_relevant_rank'])
        self.assertEqual(metrics['reciprocal_rank'], 0.0)

    def test_case_9_empty_expected_chunks(self):
        expected = []
        retrieved = ["chunk_1", "chunk_2"]
        metrics = calculate_metrics(expected, retrieved, k=5)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['precision'], 0.0)
        self.assertFalse(metrics['hit'])

    def test_case_10_invalid_or_negative_k(self):
        expected = ["chunk_1"]
        retrieved = ["chunk_1"]
        metrics = calculate_metrics(expected, retrieved, k=-5)
        self.assertEqual(metrics['k'], 5) # Fallback to default K=5


class APIEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dataset = Dataset.objects.create(name="Test Dataset", description="Testing")
        self.question = EvaluationQuestion.objects.create(
            dataset=self.dataset,
            question="What is RAG?",
            expected_chunks=["chunk_1"],
            retrieved_chunks=["chunk_1", "chunk_2"]
        )
        evaluate_dataset(self.dataset)

    def test_get_datasets(self):
        response = self.client.get(reverse('api_datasets_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_metrics(self):
        response = self.client.get(reverse('api_metrics'), {'dataset_id': self.dataset.id, 'k': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_questions'], 1)
        self.assertEqual(response.data['hit_rate'], 100.0)

    def test_upload_valid_json(self):
        data = {
            "name": "Uploaded Dataset",
            "description": "Via JSON raw",
            "raw_json": '[{"question": "How to reset pass?", "expected_chunks": ["c1"], "retrieved_chunks": ["c1", "c2"]}]'
        }
        response = self.client.post(reverse('api_datasets_upload'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Dataset.objects.count(), 2)
