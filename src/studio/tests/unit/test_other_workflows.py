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
    assert result.ok is True
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


def test_model_training_workflow_prepare_training_outcome_handles_validation_error():
    workflow = ModelTrainingWorkflow()

    outcome = workflow.prepare_training_outcome(
        {
            "model_name": "gpt2",
            "train_test_split_ratio": "9",
        }
    )

    assert outcome.ok is False
    assert outcome.failure_kind == "validation_error"
    assert "train_test_split_ratio" in outcome.error_message


def test_model_training_workflow_execute_training_success(monkeypatch):
    workflow = ModelTrainingWorkflow()

    monkeypatch.setattr(workflow.training_service, "get_model_size", lambda *_a, **_k: 2_000_000_000)
    monkeypatch.setattr(workflow.training_service, "validate_training_config", lambda *_a, **_k: None)

    class _Executor:
        def execute(self, *, config, precision, target_modules):
            return types.SimpleNamespace(ok=True, status="accepted", detail="queued", metadata={"p": precision, "m": target_modules, "n": config.model_name})

    class _Store:
        def save(self, **kwargs):
            return {"status": kwargs["execution"].status, "failure_kind": kwargs["failure_kind"]}

    result = workflow.execute_training(
        {"model_name": "meta-llama/Llama-3-8B", "train_test_split_ratio": "0.1", "use_qlora": "on"},
        executor=_Executor(),
        result_store=_Store(),
    )

    assert result.ok is True
    assert result.execution.status == "accepted"
    assert result.persisted_record == {"status": "accepted", "failure_kind": None}
    assert result.resolved_precision == "4bit-qlora"


def test_model_training_workflow_execute_training_validation_failure():
    workflow = ModelTrainingWorkflow()

    class _Executor:
        def execute(self, **_kwargs):  # pragma: no cover - should never execute
            raise AssertionError("executor should not run")

    result = workflow.execute_training(
        {"model_name": "gpt2", "train_test_split_ratio": "4"},
        executor=_Executor(),
    )

    assert result.ok is False
    assert result.failure_kind == "validation_error"
    assert result.execution.status == "invalid_config"


def test_embedding_storage_workflow_returns_storage_failure_when_vector_store_write_fails(monkeypatch):
    docs = [types.SimpleNamespace(content="A")]

    class _Mgr:
        def filter(self, **_kwargs):
            return docs

    class _FailVectorSvc(_VectorSvc):
        def store_chunks_in_qdrant(self, chunks, collection_name, client=None):
            return False

    monkeypatch.setattr("studio.application.workflows.embedding_storage.SourceDocument.objects", _Mgr())

    workflow = EmbeddingStorageWorkflow(document_service=_DocSvc(), vector_store_service=_FailVectorSvc())
    result = workflow.run(
        request=types.SimpleNamespace(
            document_ids=[1],
            collection_name="col",
            max_tokens=10,
            host="localhost",
            port=6333,
        )
    )

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.code == "storage_failure"
