from qdrant_client.http.models import Datatype, Distance, HnswConfigDiff, VectorParams

from database.qdrant.base import BaseVecCol


class ChatVec(BaseVecCol):
    COLLECTION_BASE_NAME = 'chat_collection'
    COLLECTION_VERSION_NAME = '2025-04-01'
    NUMBER_OF_SHARDS = 1
    NUMBER_OF_REPLICA = 1
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
