from collections.abc import Generator

from qdrant_client.http.models import Datatype, Distance, HnswConfigDiff, VectorParams
from qdrant_client.models import PointStruct

from database.qdrant.base import BaseVecCol


class ChatVec(BaseVecCol):
    COLLECTION_BASE_NAME = 'chat_collection'
    COLLECTION_VERSION_NAME = '2025-04-01'
    PAYLOAD_COLUMNS = []
    VECTOR_CONFIG = {
        'default': VectorParams(
            size=768,
            distance=Distance.COSINE,
            datatype=Datatype.FLOAT32,
        )
    }
    HNSW_CONFIG = HnswConfigDiff(m=48, ef_construct=200)
    PAYLOAD_PARTITIONS = ['senders']
    PAYLOAD_PARTITION_TYPES = ['keyword']

    @classmethod
    def prepare_iter_points(
        cls, chunks: list[dict], emb_list: list[list[float]], batch_size: int = 250
    ) -> Generator:
        points = []
        for idx, chunk in enumerate(chunks):
            emb = emb_list[idx].tolist()
            point = PointStruct(
                id=chunk['chunk_id'],
                vector={'default': emb},
                payload={
                    'start_timestamp': chunk['start_timestamp'],
                    'end_timestamp': chunk['end_timestamp'],
                    'senders': chunk['senders'],
                    'text': chunk['text'],
                },
            )
            points.append(point)

            if len(points) == batch_size:
                yield points
                points = []

        if points:
            yield points
