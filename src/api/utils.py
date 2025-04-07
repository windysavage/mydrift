from fastapi import Request


def get_embedding_model(request: Request) -> object:
    return request.app.state.embedding_model
