from django.db import models

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    uploaded_file = models.FileField(upload_to='datasets/', blank=True, null=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class RetrieverConfig(models.Model):
    name = models.CharField(max_length=255)
    embedding_model = models.CharField(max_length=255, default='text-embedding-3-small')
    chunk_size = models.IntegerField(default=500)
    chunk_overlap = models.IntegerField(default=50)
    top_k = models.IntegerField(default=5)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.embedding_model}, size={self.chunk_size}, overlap={self.chunk_overlap})"

    class Meta:
        ordering = ['-created_at']


class EvaluationQuestion(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='questions')
    retriever_config = models.ForeignKey(RetrieverConfig, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    question = models.TextField()
    expected_chunks = models.JSONField(default=list)   # e.g., ["chunk_12", "chunk_27"]
    retrieved_chunks = models.JSONField(default=list)  # e.g., ["chunk_41", "chunk_12", "chunk_27"]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.id}: {self.question[:50]}"

    class Meta:
        ordering = ['id']


class EvaluationResult(models.Model):
    evaluation_question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE, related_name='results')
    k = models.IntegerField(default=5)
    recall = models.FloatField(default=0.0)
    precision = models.FloatField(default=0.0)
    hit = models.BooleanField(default=False)
    reciprocal_rank = models.FloatField(default=0.0)
    first_relevant_rank = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result Q{self.evaluation_question_id} @ K={self.k}: Hit={self.hit}, Recall={self.recall:.2f}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ('evaluation_question', 'k')


class DocumentChunk(models.Model):
    """Stores individual text chunks extracted from an uploaded PDF document."""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='chunks')
    chunk_id = models.CharField(max_length=100)          # e.g. "pdf_p3_c12"
    page = models.IntegerField(default=1)
    chunk_index = models.IntegerField(default=0)
    content = models.TextField()
    word_count = models.IntegerField(default=0)

    def __str__(self):
        return f"[{self.dataset.name}] {self.chunk_id} (p{self.page})"

    class Meta:
        ordering = ['chunk_index']
