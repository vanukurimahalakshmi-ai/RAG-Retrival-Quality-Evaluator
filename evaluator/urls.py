from django.urls import path
from evaluator import views

urlpatterns = [
    # Auth Views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Page Views
    path('', views.dashboard_view, name='dashboard'),
    path('datasets/', views.datasets_view, name='datasets'),
    path('evaluation/', views.evaluation_view, name='evaluation'),
    path('questions/<int:pk>/', views.question_detail_view, name='question_detail'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('comparison/', views.comparison_view, name='comparison'),
    path('chunking/', views.chunking_view, name='chunking'),
    path('settings/', views.settings_view, name='settings'),

    # API Endpoints
    path('api/datasets/', views.DatasetListCreateAPIView.as_view(), name='api_datasets_list'),
    path('api/datasets/upload/', views.DatasetUploadAPIView.as_view(), name='api_datasets_upload'),
    path('api/datasets/upload-pdf/', views.PDFUploadAPIView.as_view(), name='api_datasets_upload_pdf'),
    path('api/datasets/load-demo/', views.LoadDemoDataAPIView.as_view(), name='api_datasets_load_demo'),
    path('api/datasets/<int:pk>/', views.DatasetDetailAPIView.as_view(), name='api_datasets_detail'),
    path('api/datasets/<int:pk>/quality/', views.PDFQualityAPIView.as_view(), name='api_datasets_quality'),
    path('api/datasets/<int:pk>/ask/', views.PDFAskAPIView.as_view(), name='api_datasets_ask'),

    path('api/evaluations/', views.EvaluationListAPIView.as_view(), name='api_evaluations_list'),
    path('api/evaluations/<int:pk>/', views.EvaluationDetailAPIView.as_view(), name='api_evaluations_detail'),
    path('api/evaluations/run/', views.RunEvaluationAPIView.as_view(), name='api_evaluations_run'),

    path('api/metrics/', views.MetricsAPIView.as_view(), name='api_metrics'),
    path('api/analytics/', views.AnalyticsAPIView.as_view(), name='api_analytics'),
    path('api/comparison/', views.ComparisonAPIView.as_view(), name='api_comparison'),
    path('api/retrievers/', views.RetrieverConfigListCreateAPIView.as_view(), name='api_retrievers'),

    path('api/export/csv/', views.ExportCSVAPIView.as_view(), name='api_export_csv'),
    path('api/export/json/', views.ExportJSONAPIView.as_view(), name='api_export_json'),
]
