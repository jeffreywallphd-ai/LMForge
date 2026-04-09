from rest_framework import serializers
from studio.domain.models import ModelStats


class ModelStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelStats
        fields = ["id", "model_name", "dataset", "ROUGE1", "ROUGE2", "ROUGE_L", "ROUGE_LSum", "BERTScoreF1", "BERTScorePrecision", "BERTScoreRecall", "STSScore", "created_at"]
