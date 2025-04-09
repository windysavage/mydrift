import attr
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from settings import get_settings


@attr.s(auto_attribs=True)
class RandomEncoder:
    embedding_dim: int = 768

    def encode(
        self, sentences: list[str], show_progress_bar: bool = False
    ) -> np.ndarray:
        return np.random.rand(len(sentences), self.embedding_dim)


@attr.s(auto_attribs=True)
class Encoder:
    model_name: str = 'jinaai/jina-embeddings-v2-base-zh'
    max_seq_length: int = 1024

    def __attrs_post_init__(self) -> None:
        if get_settings().ENVIRONMENT == 'production':
            self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
            self.model.max_seq_length = self.max_seq_length
            device = 'mps' if torch.backends.mps.is_available() else 'cpu'
            self.model.to(torch.device(device))

        else:
            self.model = RandomEncoder(embedding_dim=768)

    def encode(
        self, sentences: list[str], show_progress_bar: bool = False
    ) -> np.ndarray:
        return self.model.encode(
            sentences=sentences, show_progress_bar=show_progress_bar
        )
