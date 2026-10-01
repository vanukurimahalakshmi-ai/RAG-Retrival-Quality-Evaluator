from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

from evaluator.models import Dataset, EvaluationQuestion, EvaluationResult, RetrieverConfig, DocumentChunk
from evaluator.serializers import (
    DatasetSerializer, EvaluationQuestionSerializer, EvaluationResultSerializer,
    DatasetUploadSerializer, RetrieverConfigSerializer
)
from evaluator.services.evaluation import evaluate_dataset, evaluate_question
from evaluator.services.analytics import get_dashboard_analytics, compare_retrievers
from evaluator.services.export import export_results_csv, export_results_json
from evaluator.services.demo_data import load_demo_data
from evaluator.services.pdf_processor import process_pdf_document
from evaluator.services.pdf_quality import assess_document_quality, search_chunks


# ==========================================
# Authentication Views
# ==========================================

def login_view(request):
    """Handles User Login with username or email."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
    error = None

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        if not username_or_email or not password:
            error = 'Please enter both username/email and password.'
        else:
            # Check if user passed an email instead of username
            user_obj = None
            if '@' in username_or_email:
                user_match = User.objects.filter(email__iexact=username_or_email).first()
                if user_match:
                    user_obj = authenticate(request, username=user_match.username, password=password)
            
            if user_obj is None:
                user_obj = authenticate(request, username=username_or_email, password=password)

            if user_obj is not None:
                if not user_obj.is_active:
                    error = 'This account has been disabled.'
                else:
                    login(request, user_obj)
                    if not remember_me:
                        request.session.set_expiry(0)  # Expires on browser close
                    else:
                        request.session.set_expiry(1209600)  # 2 weeks
                    messages.success(request, f'Welcome back, {user_obj.username}!')
                    return redirect(next_url)
            else:
                error = 'Invalid username/email or password.'

    return render(request, 'login.html', {'error': error, 'next': next_url})


def register_view(request):
    """Handles User Registration with input validation and auto-login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    form_data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        form_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
        }

        if not username or not email or not password or not confirm_password:
            error = 'All fields marked with an asterisk (*) are required.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters long.'
        elif not username.replace('_', '').replace('-', '').isalnum():
            error = 'Username can only contain alphanumeric characters, hyphens, and underscores.'
        elif User.objects.filter(username__iexact=username).exists():
            error = f'Username "{username}" is already taken. Please choose another.'
        elif User.objects.filter(email__iexact=email).exists():
            error = 'An account with this email address already exists. Please log in.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match. Please verify and try again.'
        else:
            # Create user and log in
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name
            )
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome to RAG Evaluator, {user.username}.')
            return redirect('dashboard')

    return render(request, 'register.html', {'error': error, 'form_data': form_data})


def logout_view(request):
    """Logs out the user and redirects to login."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ==========================================
# Template HTML Views
# ==========================================

def dashboard_view(request):
    # Auto load demo data if database is empty
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'dashboard.html')


def datasets_view(request):
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'datasets.html')


def evaluation_view(request):
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'evaluation.html')


def question_detail_view(request, pk):
    question = get_object_or_404(EvaluationQuestion, pk=pk)
    # Ensure evaluations are calculated
    evaluate_question(question)
    return render(request, 'question_detail.html', {'question_id': pk})


def analytics_view(request):
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'analytics.html')


def comparison_view(request):
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'comparison.html')


def chunking_view(request):
    if Dataset.objects.count() == 0:
        load_demo_data()
    return render(request, 'chunking.html')


def settings_view(request):
    return render(request, 'settings.html')


# ==========================================
# REST API Endpoints
# ==========================================

class DatasetListCreateAPIView(APIView):
    def get(self, request):
        datasets = Dataset.objects.all()
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data)


class DatasetUploadAPIView(APIView):
    def post(self, request):
        serializer = DatasetUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        name = validated_data['name']
        description = validated_data.get('description', '')
        file_obj = validated_data.get('file')
        retriever_config_id = validated_data.get('retriever_config_id')
        parsed_questions = validated_data['parsed_questions']

        retriever_config = None
        if retriever_config_id:
            retriever_config = RetrieverConfig.objects.filter(id=retriever_config_id).first()

        dataset = Dataset.objects.create(
            name=name,
            description=description,
            uploaded_file=file_obj if file_obj else None
        )

        for item in parsed_questions:
            EvaluationQuestion.objects.create(
                dataset=dataset,
                retriever_config=retriever_config,
                question=item['question'],
                expected_chunks=item['expected_chunks'],
                retrieved_chunks=item['retrieved_chunks']
            )

        # Run evaluation metrics engine automatically
        evaluate_dataset(dataset)

        return Response({
            'message': f"Dataset '{name}' successfully created with {len(parsed_questions)} questions.",
            'dataset': DatasetSerializer(dataset).data
        }, status=status.HTTP_201_CREATED)


class DatasetDetailAPIView(APIView):
    def get(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        serializer = DatasetSerializer(dataset)
        return Response(serializer.data)

    def delete(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        dataset.delete()
        return Response({'message': f'Dataset {pk} successfully deleted.'}, status=status.HTTP_204_NO_CONTENT)


class PDFUploadAPIView(APIView):
    """Upload a PDF file, auto-extract text, chunk it, generate evaluation questions, and run the evaluation engine."""

    def post(self, request):
        file_obj = request.FILES.get('file')
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()
        retriever_config_id = request.data.get('retriever_config_id')

        try:
            chunk_size = int(request.data.get('chunk_size', 150))
        except (TypeError, ValueError):
            chunk_size = 150

        try:
            overlap = int(request.data.get('overlap', 30))
        except (TypeError, ValueError):
            overlap = 30

        if not file_obj:
            return Response({'error': 'No PDF file was provided.'}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith('.pdf'):
            return Response({'error': 'Only .pdf files are supported.'}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size == 0:
            return Response({'error': 'Uploaded file is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > 50 * 1024 * 1024:  # 50 MB limit
            return Response({'error': 'PDF file is too large. Maximum size is 50 MB.'}, status=status.HTTP_400_BAD_REQUEST)

        if not name:
            import os
            name = os.path.splitext(file_obj.name)[0]

        try:
            pdf_bytes = file_obj.read()
            result = process_pdf_document(pdf_bytes, chunk_size_words=chunk_size, overlap_words=overlap)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to process PDF: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        questions_data = result.get('questions', [])
        if not questions_data:
            return Response({'error': 'No evaluation questions could be generated from this PDF. The document may be too short or image-only.'}, status=status.HTTP_400_BAD_REQUEST)

        retriever_config = None
        if retriever_config_id:
            retriever_config = RetrieverConfig.objects.filter(id=retriever_config_id).first()

        file_obj.seek(0)
        dataset = Dataset.objects.create(
            name=name,
            description=description or f'Auto-generated from PDF ({result["total_pages"]} pages, {result["total_chunks"]} chunks)',
            uploaded_file=file_obj
        )

        created_questions = []
        for item in questions_data:
            q = EvaluationQuestion.objects.create(
                dataset=dataset,
                retriever_config=retriever_config,
                question=item['question'],
                expected_chunks=item['expected_chunks'],
                retrieved_chunks=item['retrieved_chunks']
            )
            created_questions.append(q)

        # Persist all text chunks so Q&A search works later
        chunk_objs = [
            DocumentChunk(
                dataset=dataset,
                chunk_id=ch['chunk_id'],
                page=ch['page'],
                chunk_index=ch['chunk_index'],
                content=ch['content'],
                word_count=ch['word_count'],
            )
            for ch in result.get('chunks', [])
        ]
        if chunk_objs:
            DocumentChunk.objects.bulk_create(chunk_objs)

        # Run evaluation metrics engine
        evaluate_dataset(dataset)

        # Quality assessment
        quality = assess_document_quality(result.get('chunks', []), result['total_pages'])

        return Response({
            'message': f"PDF '{name}' processed successfully.",
            'total_pages': result['total_pages'],
            'total_chunks': result['total_chunks'],
            'questions_generated': len(created_questions),
            'quality': quality,
            'dataset': DatasetSerializer(dataset).data
        }, status=status.HTTP_201_CREATED)


class LoadDemoDataAPIView(APIView):
    def post(self, request):
        dataset = load_demo_data()
        return Response({
            'message': 'Demo dataset and evaluation metrics successfully loaded.',
            'dataset': DatasetSerializer(dataset).data
        }, status=status.HTTP_200_OK)


class PDFQualityAPIView(APIView):
    """Return the quality report for an already-uploaded dataset's chunks."""

    def get(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        chunks_qs = DocumentChunk.objects.filter(dataset=dataset).values(
            'chunk_id', 'page', 'chunk_index', 'content', 'word_count'
        )
        chunks = list(chunks_qs)
        if not chunks:
            return Response(
                {'error': 'No stored chunks found. This dataset was not uploaded as a PDF.'},
                status=status.HTTP_404_NOT_FOUND
            )
        total_pages = dataset.chunks.values('page').distinct().count()
        quality = assess_document_quality(chunks, total_pages)
        quality['dataset_id'] = pk
        quality['dataset_name'] = dataset.name
        return Response(quality)


class PDFAskAPIView(APIView):
    """Keyword/TF-IDF Q&A — ask a question about a PDF dataset's content."""

    def post(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        query = (request.data.get('question') or '').strip()
        if not query:
            return Response({'error': 'Please provide a question.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(query) > 500:
            return Response({'error': 'Question is too long (max 500 characters).'}, status=status.HTTP_400_BAD_REQUEST)

        top_k = min(int(request.data.get('top_k', 5)), 10)
        result = search_chunks(query, dataset_id=pk, top_k=top_k)
        result['dataset_name'] = dataset.name
        return Response(result)


class EvaluationListAPIView(APIView):
    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        k = int(request.query_params.get('k', 5))
        search = request.query_params.get('search', '').strip()
        hit_filter = request.query_params.get('hit')
        min_recall = request.query_params.get('min_recall')
        max_recall = request.query_params.get('max_recall')
        ordering = request.query_params.get('ordering', '-id')

        # Select evaluation questions with their result @ k
        questions_qs = EvaluationQuestion.objects.all().select_related('dataset', 'retriever_config')

        if dataset_id:
            questions_qs = questions_qs.filter(dataset_id=dataset_id)
        if search:
            questions_qs = questions_qs.filter(Q(question__icontains=search) | Q(expected_chunks__icontains=search) | Q(retrieved_chunks__icontains=search))

        results_qs = EvaluationResult.objects.filter(k=k, evaluation_question__in=questions_qs)

        if hit_filter is not None and hit_filter != '':
            is_hit = hit_filter.lower() in ['true', '1', 'yes']
            results_qs = results_qs.filter(hit=is_hit)

        if min_recall is not None and min_recall != '':
            try:
                results_qs = results_qs.filter(recall__gte=float(min_recall))
            except ValueError:
                pass

        if max_recall is not None and max_recall != '':
            try:
                results_qs = results_qs.filter(recall__lte=float(max_recall))
            except ValueError:
                pass

        # Handle ordering
        if ordering == 'recall_desc':
            results_qs = results_qs.order_by('-recall', '-precision')
        elif ordering == 'recall_asc':
            results_qs = results_qs.order_by('recall', 'precision')
        elif ordering == 'precision_desc':
            results_qs = results_qs.order_by('-precision')
        elif ordering == 'mrr_desc':
            results_qs = results_qs.order_by('-reciprocal_rank')
        else:
            results_qs = results_qs.order_by('-id')

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        total_count = results_qs.count()

        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results_qs[start:end]

        results_data = []
        for res in paginated_results:
            q = res.evaluation_question
            results_data.append({
                'id': q.id,
                'question': q.question,
                'dataset_name': q.dataset.name,
                'retriever_name': q.retriever_config.name if q.retriever_config else 'Default',
                'expected_chunks': q.expected_chunks,
                'retrieved_chunks': q.retrieved_chunks,
                'k': res.k,
                'recall': res.recall,
                'precision': res.precision,
                'hit': res.hit,
                'reciprocal_rank': res.reciprocal_rank,
                'first_relevant_rank': res.first_relevant_rank
            })

        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size if total_count > 0 else 1,
            'k': k,
            'results': results_data
        })


class EvaluationDetailAPIView(APIView):
    def get(self, request, pk):
        question = get_object_or_404(EvaluationQuestion, pk=pk)
        k = int(request.query_params.get('k', 5))
        
        # Ensure results for this question exist
        evaluate_question(question)
        
        serializer = EvaluationQuestionSerializer(question)
        data = serializer.data

        # Highlight which retrieved chunks are relevant
        expected_set = set(str(c).strip() for c in question.expected_chunks)
        ranked_chunks = []
        for idx, chunk in enumerate(question.retrieved_chunks, start=1):
            is_relevant = str(chunk).strip() in expected_set
            ranked_chunks.append({
                'rank': idx,
                'chunk': chunk,
                'is_relevant': is_relevant
            })

        data['ranked_retrieved_chunks'] = ranked_chunks
        return Response(data)


class RunEvaluationAPIView(APIView):
    def post(self, request):
        dataset_id = request.data.get('dataset_id')
        k_values = request.data.get('k_values', [1, 3, 5, 10])

        if dataset_id:
            dataset = get_object_or_404(Dataset, pk=dataset_id)
            results = evaluate_dataset(dataset, k_values=k_values)
            msg = f"Re-evaluated {dataset.questions.count()} questions in dataset '{dataset.name}' for K={k_values}."
        else:
            total_questions = 0
            for d in Dataset.objects.all():
                evaluate_dataset(d, k_values=k_values)
                total_questions += d.questions.count()
            msg = f"Re-evaluated all {total_questions} questions across all datasets for K={k_values}."

        return Response({'message': msg}, status=status.HTTP_200_OK)


class MetricsAPIView(APIView):
    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        retriever_id = request.query_params.get('retriever_id')
        k = int(request.query_params.get('k', 5))
        
        dataset_id = int(dataset_id) if dataset_id else None
        retriever_id = int(retriever_id) if retriever_id else None
        
        analytics = get_dashboard_analytics(dataset_id=dataset_id, k=k, retriever_config_id=retriever_id)
        return Response(analytics)


class AnalyticsAPIView(APIView):
    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        retriever_id = request.query_params.get('retriever_id')
        k = int(request.query_params.get('k', 5))

        dataset_id = int(dataset_id) if dataset_id else None
        retriever_id = int(retriever_id) if retriever_id else None

        analytics = get_dashboard_analytics(dataset_id=dataset_id, k=k, retriever_config_id=retriever_id)
        return Response(analytics)


class ComparisonAPIView(APIView):
    def get(self, request):
        config_a_id = request.query_params.get('config_a')
        config_b_id = request.query_params.get('config_b')
        k = int(request.query_params.get('k', 5))

        configs = RetrieverConfig.objects.all()
        if configs.count() < 2 and config_a_id is None:
            # Auto populate demo retrievers if needed
            load_demo_data()
            configs = RetrieverConfig.objects.all()

        if not config_a_id and configs.exists():
            config_a_id = configs[0].id
        if not config_b_id and configs.count() > 1:
            config_b_id = configs[1].id
        elif not config_b_id:
            config_b_id = config_a_id

        comparison_data = compare_retrievers(int(config_a_id), int(config_b_id), k=k)
        comparison_data['all_configs'] = RetrieverConfigSerializer(RetrieverConfig.objects.all(), many=True).data
        return Response(comparison_data)


class RetrieverConfigListCreateAPIView(generics.ListCreateAPIView):
    queryset = RetrieverConfig.objects.all()
    serializer_class = RetrieverConfigSerializer


class ExportCSVAPIView(APIView):
    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        k = int(request.query_params.get('k', 5))
        dataset_id = int(dataset_id) if dataset_id else None

        csv_content = export_results_csv(dataset_id=dataset_id, k=k)
        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"rag_evaluation_results_k{k}.csv" if not dataset_id else f"dataset_{dataset_id}_k{k}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ExportJSONAPIView(APIView):
    def get(self, request):
        dataset_id = request.query_params.get('dataset_id')
        k = int(request.query_params.get('k', 5))
        dataset_id = int(dataset_id) if dataset_id else None

        json_content = export_results_json(dataset_id=dataset_id, k=k)
        response = HttpResponse(json_content, content_type='application/json')
        filename = f"rag_evaluation_results_k{k}.json" if not dataset_id else f"dataset_{dataset_id}_k{k}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
