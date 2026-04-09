from types import SimpleNamespace

import pytest

qdrant_client = pytest.importorskip("qdrant_client")
pytest.importorskip("sentence_transformers")

import studio.infrastructure.vectorstores.qdrant as qdrant


class _FakeClient:
    def __init__(self):
        self.recreate_calls = []
        self.upsert_calls = []
        self.search_calls = []

    def get_collections(self):
        return SimpleNamespace(collections=[])

    def recreate_collection(self, **kwargs):
        self.recreate_calls.append(kwargs)

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return [SimpleNamespace(id="p1", score=0.9, payload={"question": "Q"})]


class _FakeModel:
    def encode(self, texts, **_kwargs):
        return SimpleNamespace(tolist=lambda: [[float(len(t))] for t in texts])


def test_get_embedding_model_and_client_are_cached(monkeypatch):
    qdrant._embedding_model = None
    qdrant._qdrant_client = None

    monkeypatch.setattr("studio.infrastructure.vectorstores.qdrant.SentenceTransformer", lambda *_a: _FakeModel())
    monkeypatch.setattr("studio.infrastructure.vectorstores.qdrant.QdrantClient", lambda **_k: _FakeClient())

    first_model = qdrant.get_embedding_model()
    second_model = qdrant.get_embedding_model()
    first_client = qdrant.get_qdrant_client()
    second_client = qdrant.get_qdrant_client()

    assert first_model is second_model
    assert first_client is second_client


def test_ensure_collection_creates_when_missing(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda *args, **kwargs: client)

    qdrant.ensure_collection(collection_name="my_col", vector_size=12, distance="dot")

    assert client.recreate_calls
    recreate = client.recreate_calls[0]
    assert recreate["collection_name"] == "my_col"
    assert recreate["vectors_config"].size == 12


def test_upsert_and_search_flow(monkeypatch):
    client = _FakeClient()

    monkeypatch.setattr(qdrant, "get_qdrant_client", lambda *args, **kwargs: client)
    monkeypatch.setattr(qdrant, "embed_texts", lambda texts: [[0.1, 0.2] for _ in texts])
    calls = []
    monkeypatch.setattr(
        qdrant,
        "ensure_collection",
        lambda collection_name, vector_size, distance: calls.append((collection_name, vector_size, distance)),
    )

    upserted = qdrant.upsert_qa_items(
        [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2", "vector": [999]}],
        collection_name="qa_col",
    )

    assert upserted["upserted"] == 2
    assert len(upserted["point_ids"]) == 2
    assert calls == [("qa_col", 2, "cosine")]
    assert client.upsert_calls[0]["collection_name"] == "qa_col"
    assert all("vector" not in p.payload for p in client.upsert_calls[0]["points"])

    hits = qdrant.search_similar("What?", top_k=3, collection_name="qa_col")
    assert hits == [{"id": "p1", "score": 0.9, "payload": {"question": "Q"}}]
    assert client.search_calls[0]["limit"] == 3


def test_upsert_empty_short_circuit():
    assert qdrant.upsert_qa_items([]) == {"upserted": 0}
