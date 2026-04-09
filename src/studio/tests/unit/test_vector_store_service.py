import types

from studio.application.services.vector_store_service import VectorStoreService


class _QModels:
    class Distance:
        COSINE = "cosine"

    class VectorParams:
        def __init__(self, size, distance):
            self.size = size
            self.distance = distance

    class PointStruct:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload


class _Client:
    def __init__(self):
        self.created = []
        self.upserts = []

    def get_collections(self):
        return types.SimpleNamespace(collections=[types.SimpleNamespace(name="existing")])

    def create_collection(self, **kwargs):
        self.created.append(kwargs)

    def count(self, collection_name):
        return types.SimpleNamespace(count=3)

    def upsert(self, collection_name, points):
        self.upserts.append((collection_name, points))

    def scroll(self, collection_name, limit, with_payload, offset):
        if offset is None:
            return [types.SimpleNamespace(payload={"text": "chunk-1"})], "next"
        return [types.SimpleNamespace(payload={"text": "chunk-2"})], None


def test_safe_import_qdrant_returns_none_when_missing(monkeypatch):
    service = VectorStoreService()

    def _import(_name):
        raise ImportError

    monkeypatch.setattr("importlib.import_module", _import)
    qdrant_cls, qmodels = service.safe_import_qdrant()
    assert qdrant_cls is None and qmodels is None


def test_ensure_collection_exists_creates_only_when_absent(monkeypatch):
    service = VectorStoreService()
    client = _Client()

    monkeypatch.setattr(service, "safe_import_qdrant", lambda: (object, _QModels))
    service.ensure_collection_exists(client, "missing", vector_size=5)
    service.ensure_collection_exists(client, "existing", vector_size=5)

    assert len(client.created) == 1
    assert client.created[0]["collection_name"] == "missing"


def test_store_chunks_in_qdrant_success_path(monkeypatch):
    service = VectorStoreService()
    client = _Client()
    monkeypatch.setattr(service, "safe_import_qdrant", lambda: (object, _QModels))

    class _Emb:
        def encode(self, chunks):
            return types.SimpleNamespace(tolist=lambda: [[0.1, 0.2] for _ in chunks])

    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        lambda _name: _Emb(),
    )

    stored = service.store_chunks_in_qdrant(["a", "b"], "mycol", client=client)

    assert stored is True
    assert client.upserts
    upsert_points = client.upserts[0][1]
    assert [p.id for p in upsert_points] == [4, 5]


def test_store_chunks_in_qdrant_returns_false_for_missing_inputs(monkeypatch):
    service = VectorStoreService()
    assert service.store_chunks_in_qdrant([], "c") is False
    monkeypatch.setattr(service, "get_client", lambda: None)
    assert service.store_chunks_in_qdrant(["a"], "c", client=None) is False


def test_fetch_chunks_from_collection_pages_until_offset_none():
    service = VectorStoreService()
    client = _Client()

    chunks = service.fetch_chunks_from_collection("c", batch_size=1, client=client)

    assert chunks == ["chunk-1", "chunk-2"]
