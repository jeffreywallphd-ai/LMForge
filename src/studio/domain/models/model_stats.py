"""Domain model storing evaluation metrics per model/dataset run."""

from django.db import models


class ModelStats(models.Model):
    model_name = models.CharField(max_length=255)
    dataset = models.CharField(max_length=255)
    ROUGE1 = models.FloatField()
    ROUGE2 = models.FloatField()
    ROUGE_L = models.FloatField()
    ROUGE_LSum = models.FloatField()
    BERTScoreF1 = models.FloatField()
    BERTScorePrecision = models.FloatField()
    BERTScoreRecall = models.FloatField()
    STSScore = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lmforge_core_modelstats"

    def __str__(self) -> str:
        return f"{self.model_name} - {self.dataset}"
