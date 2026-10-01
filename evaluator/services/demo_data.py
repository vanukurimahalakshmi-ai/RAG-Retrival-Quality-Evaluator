from django.contrib.auth.models import User
from evaluator.models import Dataset, EvaluationQuestion, RetrieverConfig
from evaluator.services.evaluation import evaluate_dataset

def load_demo_data():
    """
    Populate the database with realistic demo datasets, retriever configurations,
    evaluation questions, and calculated evaluation results across K=1, 3, 5, 10.
    """
    # 0. Ensure Demo User exists
    if not User.objects.filter(username="demo_user").exists():
        User.objects.create_user(
            username="demo_user",
            email="demo@example.com",
            password="ragdemo123",
            first_name="Demo Evaluator"
        )

    # 1. Create Retriever Configurations
    config_a, _ = RetrieverConfig.objects.get_or_create(
        name="Dense Retriever - BGE-Large",
        defaults={
            'embedding_model': 'BAAI/bge-large-en-v1.5',
            'chunk_size': 500,
            'chunk_overlap': 50,
            'top_k': 5,
            'description': 'High-density vector search using BGE large embedding model with standard 500 token chunks.'
        }
    )

    config_b, _ = RetrieverConfig.objects.get_or_create(
        name="Hybrid Retriever - BM25 + OpenAI v3",
        defaults={
            'embedding_model': 'text-embedding-3-small',
            'chunk_size': 800,
            'chunk_overlap': 100,
            'top_k': 5,
            'description': 'Hybrid keyword (BM25) and dense semantic vector search with larger 800 token chunk size.'
        }
    )

    # 2. Create Primary Demo Dataset
    dataset, created = Dataset.objects.get_or_create(
        name="Enterprise KB & Support Policy Dataset (Demo)",
        defaults={
            'description': 'Standard evaluation benchmark covering customer support policies, SLA guidelines, technical specs, and refund terms.',
            'is_demo': True
        }
    )

    if not created and dataset.questions.count() > 0:
        # Evaluate to ensure results exist
        evaluate_dataset(dataset)
        return dataset

    demo_questions_data = [
        {
            "question": "What is the standard refund policy for annual enterprise subscription plans?",
            "expected_chunks": ["chunk_refund_12", "chunk_refund_27"],
            "retrieved_chunks": ["chunk_refund_12", "chunk_refund_27", "chunk_billing_05", "chunk_terms_99"],
            "retriever_config": config_a
        },
        {
            "question": "How do I configure OAuth 2.0 single sign-on with Azure AD?",
            "expected_chunks": ["chunk_sso_10", "chunk_sso_11"],
            "retrieved_chunks": ["chunk_general_01", "chunk_sso_10", "chunk_sso_11", "chunk_auth_44"],
            "retriever_config": config_a
        },
        {
            "question": "What are the rate limits and throttling policies for the REST API v2?",
            "expected_chunks": ["chunk_api_50"],
            "retrieved_chunks": ["chunk_api_50", "chunk_api_51", "chunk_sdk_03", "chunk_webhooks_02"],
            "retriever_config": config_a
        },
        {
            "question": "Where can I download the GDPR data processing agreement (DPA)?",
            "expected_chunks": ["chunk_legal_88"],
            "retrieved_chunks": ["chunk_privacy_01", "chunk_cookies_09", "chunk_tos_12", "chunk_faq_04"],
            "retriever_config": config_a
        },
        {
            "question": "What is the maximum file upload size for batch document processing?",
            "expected_chunks": ["chunk_doc_04", "chunk_doc_05"],
            "retrieved_chunks": ["chunk_doc_04", "chunk_limits_01", "chunk_storage_20"],
            "retriever_config": config_a
        },
        {
            "question": "How do I reset my multi-factor authentication (MFA) security device?",
            "expected_chunks": ["chunk_mfa_33"],
            "retrieved_chunks": ["chunk_login_02", "chunk_password_10", "chunk_mfa_33", "chunk_help_77"],
            "retriever_config": config_a
        },
        {
            "question": "What are the network firewall requirements for hybrid deployment agents?",
            "expected_chunks": ["chunk_net_70", "chunk_net_71", "chunk_net_72"],
            "retrieved_chunks": ["chunk_net_70", "chunk_proxy_02", "chunk_net_71", "chunk_net_72", "chunk_dns_05"],
            "retriever_config": config_a
        },
        {
            "question": "Can I export workspace audit logs to AWS S3 or Datadog?",
            "expected_chunks": ["chunk_audit_90"],
            "retrieved_chunks": ["chunk_audit_90", "chunk_aws_12", "chunk_datadog_03"],
            "retriever_config": config_a
        },
        {
            "question": "What are the GPU memory requirements for fine-tuning custom embeddings?",
            "expected_chunks": ["chunk_gpu_15", "chunk_gpu_16"],
            "retriever_config": config_b,
            "retrieved_chunks": ["chunk_gpu_15", "chunk_gpu_16", "chunk_cuda_01", "chunk_models_09"]
        },
        {
            "question": "How does vector index quantization affect query latency and recall precision?",
            "expected_chunks": ["chunk_hnsw_01", "chunk_ivf_08"],
            "retrieved_chunks": ["chunk_hnsw_01", "chunk_benchmarks_40", "chunk_ivf_08", "chunk_faiss_10"],
            "retriever_config": config_b
        },
        {
            "question": "What is the procedure for zero-downtime database schema migration?",
            "expected_chunks": ["chunk_db_60"],
            "retrieved_chunks": ["chunk_deploy_01", "chunk_docker_02", "chunk_k8s_03", "chunk_db_60"],
            "retriever_config": config_b
        },
        {
            "question": "How are expired API keys revoked and automatically rotated?",
            "expected_chunks": ["chunk_keys_14"],
            "retrieved_chunks": ["chunk_keys_99", "chunk_auth_01", "chunk_tokens_05"], # Failure
            "retriever_config": config_b
        }
    ]

    for item in demo_questions_data:
        EvaluationQuestion.objects.create(
            dataset=dataset,
            retriever_config=item['retriever_config'],
            question=item['question'],
            expected_chunks=item['expected_chunks'],
            retrieved_chunks=item['retrieved_chunks']
        )

    # Calculate metrics for all questions in demo dataset
    evaluate_dataset(dataset)
    return dataset
