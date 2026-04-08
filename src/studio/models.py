"""Django model registration for the Studio app.

Models are implemented in ``studio.domain.models`` to keep domain concerns separate
from presentation and infrastructure layers.
"""

from src.studio.domain.models.conversations import Conversation
from src.studio.domain.models.dataset_artifacts import Answer, DatasetArtifact, Question, ReviewAnswer, Reviewer
from src.studio.domain.models.model_stats import ModelStats
from src.studio.domain.models.processed_documents import License, ProcessedDocument, Source
from src.studio.domain.models.source_documents import SourceDocument, SourceDocumentMetadata

__all__ = [
    "Answer",
    "Conversation",
    "DatasetArtifact",
    "License",
    "ModelStats",
    "ProcessedDocument",
    "Question",
    "ReviewAnswer",
    "Reviewer",
    "Source",
    "SourceDocument",
    "SourceDocumentMetadata",
]
