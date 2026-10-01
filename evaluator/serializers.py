import json
import csv
from io import StringIO, TextIOWrapper
from rest_framework import serializers
from evaluator.models import Dataset, EvaluationQuestion, EvaluationResult, RetrieverConfig

class RetrieverConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetrieverConfig
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = ['id', 'name', 'description', 'uploaded_file', 'is_demo', 'created_at', 'updated_at', 'question_count']

    def get_question_count(self, obj):
        return obj.questions.count()


class EvaluationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationResult
        fields = ['id', 'k', 'recall', 'precision', 'hit', 'reciprocal_rank', 'first_relevant_rank', 'created_at']


class EvaluationQuestionSerializer(serializers.ModelSerializer):
    results = serializers.SerializerMethodField()
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    retriever_name = serializers.CharField(source='retriever_config.name', read_only=True, default='Default Retriever')

    class Meta:
        model = EvaluationQuestion
        fields = [
            'id', 'dataset', 'dataset_name', 'retriever_config', 'retriever_name',
            'question', 'expected_chunks', 'retrieved_chunks', 'created_at', 'results'
        ]

    def get_results(self, obj):
        # Return results ordered by k
        results = obj.results.all().order_by('k')
        return EvaluationResultSerializer(results, many=True).data


class DatasetUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    file = serializers.FileField(required=False)
    raw_json = serializers.CharField(required=False, allow_blank=True)
    retriever_config_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        file_obj = attrs.get('file')
        raw_json = attrs.get('raw_json')

        if not file_obj and not raw_json:
            raise serializers.ValidationError("Please provide either an uploaded file (CSV/JSON) or raw JSON content.")

        parsed_items = []

        if raw_json and raw_json.strip():
            try:
                data = json.loads(raw_json)
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    raise serializers.ValidationError("JSON data must be an array of evaluation items or a single evaluation object.")
                parsed_items = data
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")

        elif file_obj:
            filename = file_obj.name.lower()

            if file_obj.size == 0:
                raise serializers.ValidationError("Uploaded file is empty.")

            if filename.endswith('.json'):
                try:
                    content = file_obj.read().decode('utf-8')
                    file_obj.seek(0)
                    data = json.loads(content)
                    if isinstance(data, dict):
                        data = [data]
                    if not isinstance(data, list):
                        raise serializers.ValidationError("JSON file content must be a JSON array of questions.")
                    parsed_items = data
                except json.JSONDecodeError as e:
                    raise serializers.ValidationError(f"Invalid JSON syntax in file: {str(e)}")
                except UnicodeDecodeError:
                    raise serializers.ValidationError("JSON file must be UTF-8 encoded text.")

            elif filename.endswith('.csv'):
                try:
                    content = file_obj.read().decode('utf-8')
                    file_obj.seek(0)
                    csv_file = StringIO(content)
                    reader = csv.DictReader(csv_file)
                    
                    if not reader.fieldnames or 'question' not in [f.strip() for f in reader.fieldnames]:
                        raise serializers.ValidationError("CSV file missing required header column 'question'. Standard columns: question, expected_chunks, retrieved_chunks")

                    for idx, row in enumerate(reader, start=1):
                        q_text = row.get('question', '').strip()
                        exp_str = row.get('expected_chunks', '').strip()
                        ret_str = row.get('retrieved_chunks', '').strip()

                        if not q_text:
                            continue

                        # Parse expected_chunks JSON array or pipe/comma separated list
                        expected_chunks = self._parse_chunk_list(exp_str)
                        retrieved_chunks = self._parse_chunk_list(ret_str)

                        parsed_items.append({
                            'question': q_text,
                            'expected_chunks': expected_chunks,
                            'retrieved_chunks': retrieved_chunks
                        })

                except Exception as e:
                    raise serializers.ValidationError(f"Failed to parse CSV file: {str(e)}")
            else:
                raise serializers.ValidationError("Unsupported file format. Please upload a .csv or .json file.")

        if not parsed_items:
            raise serializers.ValidationError("No valid evaluation question records were found in the input.")

        validated_questions = []
        for idx, item in enumerate(parsed_items, start=1):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"Record #{idx} is not a valid JSON object.")
            
            question_text = item.get('question')
            if not question_text or not str(question_text).strip():
                raise serializers.ValidationError(f"Record #{idx} is missing required 'question' field.")

            expected_chunks = item.get('expected_chunks', [])
            retrieved_chunks = item.get('retrieved_chunks', [])

            if isinstance(expected_chunks, str):
                expected_chunks = self._parse_chunk_list(expected_chunks)
            if isinstance(retrieved_chunks, str):
                retrieved_chunks = self._parse_chunk_list(retrieved_chunks)

            if not isinstance(expected_chunks, list):
                raise serializers.ValidationError(f"Record #{idx} 'expected_chunks' must be a list of chunk IDs.")

            if not isinstance(retrieved_chunks, list):
                raise serializers.ValidationError(f"Record #{idx} 'retrieved_chunks' must be a list of chunk IDs.")

            validated_questions.append({
                'question': str(question_text).strip(),
                'expected_chunks': [str(c).strip() for c in expected_chunks if str(c).strip()],
                'retrieved_chunks': [str(c).strip() for c in retrieved_chunks if str(c).strip()]
            })

        attrs['parsed_questions'] = validated_questions
        return attrs

    def _parse_chunk_list(self, raw_str: str) -> list:
        if not raw_str:
            return []
        raw_str = raw_str.strip()
        if raw_str.startswith('[') and raw_str.endswith(']'):
            try:
                res = json.loads(raw_str)
                if isinstance(res, list):
                    return res
            except Exception:
                pass
        # Fallback split by pipe or comma
        if '|' in raw_str:
            return [s.strip() for s in raw_str.split('|') if s.strip()]
        return [s.strip() for s in raw_str.split(',') if s.strip()]
