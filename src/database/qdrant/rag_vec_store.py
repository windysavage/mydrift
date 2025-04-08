from collections.abc import Generator

from qdrant_client.http.models import Datatype, Distance, HnswConfigDiff, VectorParams
from qdrant_client.models import PointStruct

from database.qdrant.base import BaseVecStore


class RAGVecStore(BaseVecStore):
    COLLECTION_BASE_NAME = 'rag_vector_store'
    COLLECTION_VERSION_NAME = '2025-04-09'
    PAYLOAD_COLUMNS = []
    VECTOR_CONFIG = {
        'default': VectorParams(
            size=768,
            distance=Distance.COSINE,
            datatype=Datatype.FLOAT32,
        )
    }
    HNSW_CONFIG = HnswConfigDiff(m=48, ef_construct=200)

    @classmethod
    def prepare_iter_points(
        cls, chunks: list[dict], batch_size: int = 250
    ) -> Generator:
        points = []
        for chunk in chunks:
            point = PointStruct(
                id=chunk['chunk_id'],
                vector={'default': chunk['embedding']},
                payload={'source': chunk['source']},
            )
            points.append(point)

            if len(points) == batch_size:
                yield points
                points = []

        if points:
            yield points
