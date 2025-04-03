import uvicorn

from api.app import app  # noqa: F401

if __name__ == '__main__':
    uvicorn.run('api.app:app', host='0.0.0.0', reload=True)
