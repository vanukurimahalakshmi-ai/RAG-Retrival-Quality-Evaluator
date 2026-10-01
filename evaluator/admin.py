from django.contrib import admin
from evaluator.models import Dataset, RetrieverConfig, EvaluationQuestion, EvaluationResult

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_demo', 'created_at', 'updated_at')
    list_filter = ('is_demo', 'created_at')
    search_fields = ('name', 'description')

@admin.register(RetrieverConfig)
class RetrieverConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'embedding_model', 'chunk_size', 'chunk_overlap', 'top_k')
    search_fields = ('name', 'embedding_model')

@admin.register(EvaluationQuestion)
class EvaluationQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'dataset', 'retriever_config', 'question_summary', 'created_at')
    list_filter = ('dataset', 'retriever_config', 'created_at')
    search_fields = ('question', 'expected_chunks', 'retrieved_chunks')

    def question_summary(self, obj):
        return obj.question[:60] + ('...' if len(obj.question) > 60 else '')
    question_summary.short_description = 'Question'

@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'evaluation_question_id', 'k', 'recall', 'precision', 'hit', 'reciprocal_rank', 'first_relevant_rank')
    list_filter = ('k', 'hit', 'created_at')
    search_fields = ('evaluation_question__question',)
