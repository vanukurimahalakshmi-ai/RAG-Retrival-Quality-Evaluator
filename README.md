# RAG Retrieval Quality Evaluator

A complete full-stack Django web application for evaluating, inspecting, and analyzing the retrieval quality of Retrieval-Augmented Generation (RAG) pipelines.

![Theme](https://img.shields.io/badge/Theme-Dark%20Navy%20AI%2FML-0b0f17)
![Stack](https://img.shields.io/badge/Stack-Python%20%7C%20Django%20%7C%20DRF%20%7C%20Chart.js-3b82f6)

---

## 🌟 Key Features

- **Dynamic Evaluation Engine**: Calculates ground-truth metrics directly from uploaded datasets and demo data.
  - **Recall@K**: Proportion of expected relevant chunks retrieved in the top K.
  - **Precision@K**: Proportion of top K retrieved chunks that are relevant.
  - **Hit Rate**: Percentage of questions with at least 1 relevant chunk in top K.
  - **Reciprocal Rank (RR)**: `1 / rank` of the first relevant chunk (`0.0` if missed).
  - **MRR (Mean Reciprocal Rank)**: Average reciprocal rank across questions.
- **Interactive Developer Dashboard**:
  - Live summary statistics cards & cut-off K selector (K=1, 3, 5, 10).
  - Interactive Chart.js visualizers: Hit vs Miss ratio, Recall & Precision distribution curves, MRR distribution, and performance scaling across cut-off K values.
  - Failure identification list highlighting lowest-performing questions.
- **Dataset Management & Validation**:
  - Upload ground truth evaluation benchmark files in **JSON** or **CSV** formats or input raw JSON.
  - Comprehensive error validation catching invalid JSON syntax, missing fields, empty datasets, or bad chunk structures.
  - One-click built-in realistic demo dataset loader.
- **Question Inspection Detail Page**:
  - Ranked order display of retrieved chunks with visual indicators: 🟢 **Relevant Chunk** vs 🔴 **Irrelevant Chunk**.
  - Side-by-side metric break-down for individual queries.
- **Retriever Comparison**:
  - Compare two retriever models or strategies side-by-side (e.g. BGE-Large vs Hybrid BM25+OpenAI).
  - Automated delta calculation for metrics & parameters.
- **Chunking Strategy Analysis**:
  - Record and inspect performance across chunk sizes (e.g. 500 vs 800 tokens) and chunk overlap settings.
- **Dynamic Exports**:
  - Export evaluation results dynamically as **CSV** or **JSON** for downstream ML reporting.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13+, Django 6.1+, Django REST Framework 3.18+
- **Database**: SQLite (Django ORM)
- **Frontend**: Django Templates, Bootstrap 5, Vanilla CSS3 (Dark AI/ML developer styling), JavaScript (Fetch API, Chart.js 4.4+)

---

## 🚀 Quick Start & Setup Instructions

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Clone / Open Project
Navigate to the project root directory:
```bash
cd project
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Run Automated Tests
Verify all evaluation engine math, edge cases, and API endpoints:
```bash
python manage.py test
```

### 6. Start Development Server
```bash
python manage.py runserver
```

### 7. Access Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

*(Upon first load, the built-in realistic demo dataset will automatically populate the dashboard).*

---

## 📂 Dataset Upload Format Guide

### JSON Format
```json
[
  {
    "question": "What is the refund policy for annual enterprise plans?",
    "expected_chunks": ["chunk_refund_12", "chunk_refund_27"],
    "retrieved_chunks": ["chunk_refund_12", "chunk_refund_27", "chunk_billing_05", "chunk_terms_99"]
  }
]
```

### CSV Format
```csv
question,expected_chunks,retrieved_chunks
"What is the refund policy?","chunk_refund_12|chunk_refund_27","chunk_refund_12|chunk_refund_27|chunk_billing_05"
```

---

## 📐 Evaluation Metrics Definitions

| Metric | Formula / Description |
|---|---|
| **Recall@K** | $\frac{\| \text{Expected Chunks} \cap \text{Retrieved[:K]} \|}{\| \text{Expected Chunks} \|}$ |
| **Precision@K** | $\frac{\| \text{Expected Chunks} \cap \text{Retrieved[:K]} \|}{K}$ |
| **Hit Rate** | $1.0 \text{ if } (\| \text{Expected} \cap \text{Retrieved[:K]} \| > 0) \text{ else } 0.0$ |
| **Reciprocal Rank** | $\frac{1}{\text{Rank of 1st Relevant Chunk}} \text{ (if rank } \le K \text{ else } 0.0)$ |
| **MRR** | $\frac{1}{N} \sum_{i=1}^{N} \text{Reciprocal Rank}_i$ |
