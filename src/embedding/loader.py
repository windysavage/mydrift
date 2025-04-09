import torch
from sentence_transformers import SentenceTransformer


def load_encoder_by_name(
    model_name: str = 'jinaai/jina-embeddings-v2-base-zh',
) -> SentenceTransformer:
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    print(f'using {device} device')
    model = SentenceTransformer(model_name, trust_remote_code=True)
    model.max_seq_length = 1024
    model.to(torch.device(device))
    return model
