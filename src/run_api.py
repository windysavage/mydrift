import uvicorn

from app import app  # noqa: F401

if __name__ == '__main__':
    uvicorn.run('app:app', host='0.0.0.0', reload=True)
