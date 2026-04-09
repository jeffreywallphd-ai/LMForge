import types

import pandas as pd
import pytest

from studio.application.services.document_service import ScrapedPayload
from studio.application.workflows.document_ingestion import DocumentIngestionWorkflow
from studio.application.workflows.embedding_storage import EmbeddingStorageWorkflow
from studio.application.workflows.model_evaluation import ModelEvaluationWorkflow, ModelEvaluationWorkflowRequest
from studio.application.workflows.model_training import ModelTrainingWorkflow


class _DocSvc:
    def __init__(self):
        self.persisted_payload = None

    def scrape_generic_url(self, url, title=""):
        return ScrapedPayload(url=url, file_type="html", title=title or "t", content="x" * 600)

    def persist_source_document(self, payload):
        self.persisted_payload = payload
        return types.SimpleNamespace(id=11)

    def split_text(self, text, max_tokens=1000):
        return ["c1", "c2"]


class _VectorSvc:
    def get_client(self, host="localhost", port=6333):
        return {"host": host, "port": port}

    def get_existing_collections(self, client):
        return ["a", f"{client['host']}:{client['port']}"]

    def store_chunks_in_qdrant(self, chunks, collection_name, client=None):
        return bool(chunks) and bool(collection_name)

    def fetch_chunks_from_collection(self, collection_name, batch_size=100, client=None):
        return [f"{collection_name}:{batch_size}"]


class _EvalSvc:
    def model_stats(self, question, references, config):
        base = len(question) + len(references[0]) + len(config.model_name)
        return {
            "ROUGE1": base,
            "ROUGE2": 2,
            "ROUGEL": 3,
            "ROUGELSUM": 4,
            "BERTScoreF1": 5,
            "BERTScorePrecision": 6,
            "BERTScoreRecall": 7,
            "STSScore": 8,
        }


def test_document_ingestion_scrape_and_persist():
    workflow = DocumentIngestionWorkflow(document_service=_DocSvc())

    scrape_only = workflow.scrape_only(url="https://e.com", title="My title")
    saved = workflow.scrape_and_persist(url="https://e.com", title="My title")

    assert scrape_only.title == "My title"
    assert saved.persisted_document_id == 11
    assert len(saved.content_preview) == 500


def test_embedding_storage_workflow_happy_paths(monkeypatch):
    docs = [types.SimpleNamespace(content="A"), types.SimpleNamespace(content="B")]

    class _Mgr:
        def filter(self, **_kwargs):
            return docs

    monkeypatch.setattr("studio.application.workflows.embedding_storage.SourceDocument.objects", _Mgr())

    workflow = EmbeddingStorageWorkflow(document_service=_DocSvc(), vector_store_service=_VectorSvc())

    assert workflow.list_collections(host="h", port=1) == ["a", "h:1"]
    assert workflow.preview_chunks(document_ids=[1], max_tokens=10) == ["c1", "c2"]

    result = workflow.store_document_embeddings(document_ids=[1], collection_name="col", max_tokens=10)
    assert result.chunk_count == 2
    assert result.stored is True
    assert workflow.fetch_collection_chunks(collection_name="col", batch_size=7) == ["col:7"]


def test_embedding_storage_workflow_validates_inputs():
    workflow = EmbeddingStorageWorkflow(document_service=_DocSvc(), vector_store_service=_VectorSvc())
    with pytest.raises(ValueError, match="collection_name is required"):
        workflow.store_document_embeddings(document_ids=[1], collection_name="   ")


def test_model_training_workflow_prepare_training(monkeypatch):
    workflow = ModelTrainingWorkflow()

    monkeypatch.setattr(workflow.training_service, "get_model_size", lambda *_a, **_k: 2_000_000_000)
    monkeypatch.setattr(workflow.training_service, "validate_training_config", lambda *_a, **_k: None)

    plan = workflow.prepare_training(
        {
            "model_name": "meta-llama/Llama-3-8B",
            "use_qlora": "on",
            "fp16": "on",
            "bf16": "on",
        }
    )

    assert plan.model_size == 2_000_000_000
    assert plan.resolved_precision == "4bit-qlora"
    assert plan.target_modules == ["q_proj", "v_proj"]


def test_model_evaluation_workflow_load_and_aggregate(monkeypatch):
    workflow = ModelEvaluationWorkflow(evaluation_service=_EvalSvc())

    sample_df = pd.DataFrame(
        {
            "question": ["q1", "q2"],
            "reference": ["r1", "r2"],
        }
    )
    monkeypatch.setattr(workflow, "_load_dataframe", lambda _req: sample_df)

    result = workflow.evaluate_models(ModelEvaluationWorkflowRequest(models=["m1", "m2"]))

    assert set(result.keys()) == {"m1", "m2"}
    assert result["m1"]["ROUGE2"] == 2.0
    assert result["m1"]["STSScore"] == 8.0


def test_model_evaluation_workflow_load_dataframe_validation(monkeypatch):
    workflow = ModelEvaluationWorkflow(evaluation_service=_EvalSvc())

    df = pd.DataFrame({"x": [1], "y": [2]})
    monkeypatch.setattr("studio.application.workflows.model_evaluation.pd.read_csv", lambda _p: df)

    request = ModelEvaluationWorkflowRequest(models=["m"], dataset_file_path="/tmp/f.csv")
    with pytest.raises(ValueError, match="Input/Output"):
        workflow._load_dataframe(request)
