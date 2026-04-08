"""Domain models for Q/A datasets, annotations, and review artifacts."""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .processed_documents import License, ProcessedDocument, ValidityLevel


class Question(models.Model):
    question_id = models.AutoField(primary_key=True, db_column="Question_ID")
    text = models.CharField(max_length=255, db_column="Question")

    class Meta:
        db_table = "lmforge_core_question"

    def __str__(self) -> str:
        return f"Question: {self.text}"


class Answer(models.Model):
    answer_id = models.IntegerField(primary_key=True, db_column="Answer_ID")
    link = models.CharField(max_length=255, null=True, db_column="Link")
    page_num = models.IntegerField(null=True, blank=True, db_column="PageNum")
    text = models.CharField(max_length=255, db_column="Answer")
    last_day_scraped = models.DateField(db_column="LastDayScraped")
    copyright_date = models.DateField(null=True, blank=True, db_column="CopyrightDate")
    outdated_flag = models.IntegerField(null=True, blank=True, db_column="OutdatedFlag")
    flag_new_answer_id = models.IntegerField(null=True, blank=True, db_column="FlagNewAnswerID")
    answer_rating = models.IntegerField(null=True, blank=True, db_column="AnswerRating")
    validity_level = models.IntegerField(
        choices=ValidityLevel.choices,
        default=ValidityLevel.RANDOM_UNVERIFIED,
        db_column="AnswerValid",
    )
    document = models.ForeignKey(ProcessedDocument, on_delete=models.CASCADE, db_column="Doc_id")
    license = models.ForeignKey(License, on_delete=models.CASCADE, db_column="License_ID")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_column="Question_ID")

    class Meta:
        db_table = "lmforge_core_answer"

    def __str__(self) -> str:
        return (
            f"Answer {self.answer_id} - Link: {self.link} - Page: {self.page_num} - "
            f"Answer: {self.text} - Scraped: {self.last_day_scraped} - Copyright: {self.copyright_date} - "
            f"Doc: {self.document_id} - License: {self.license_id} - Question: {self.question_id} "
            f"(Status: {self.get_validity_level_display()})"
        )


class DatasetArtifact(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_column="question_id")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, db_column="answer_id")

    class Meta:
        db_table = "lmforge_core_questionanswer"

    def __str__(self) -> str:
        return f"Question: {self.question.text} - Answer: {self.answer.text}"


class Reviewer(models.Model):
    review_id = models.AutoField(primary_key=True, db_column="review_id")
    first_name = models.CharField(max_length=255, db_column="first_name")
    last_name = models.CharField(max_length=255, db_column="last_name")

    class Meta:
        db_table = "lmforge_core_reviewer"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class ReviewAnswer(models.Model):
    review_answer_id = models.AutoField(primary_key=True, db_column="RevAnswer_ID")
    score_scale = models.IntegerField(
        db_column="ScoreScale",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating between 1 (worst) and 5 (best)",
    )
    description = models.CharField(max_length=255, db_column="Description")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_column="question_id")
    reviewer = models.ForeignKey(Reviewer, on_delete=models.CASCADE, db_column="reviewer")

    class Meta:
        db_table = "lmforge_core_reviewanswer"

    def __str__(self) -> str:
        return f"ReviewAnswer {self.review_answer_id} - Score: {self.score_scale} - {self.description}"
