import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel

from api.schema import MessagePayload, UploadJsonPayload
from core.agent_handler import AgentHandler
from core.llm_handler import LLMHandler
from core.reindex_handler import ReindexHandler
from database.mongodb.base import init_mongodb_cols
from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client
from database.qdrant.base import init_qdrant_cols
from database.qdrant.client import async_qdrant_client
from embedding.loader import load_embedding_model_by_name

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_qdrant_cols()
    await init_mongodb_cols()
    app.state.embedding_model = load_embedding_model_by_name()
    yield
    print('🛑 Shutting down...')


app = FastAPI(lifespan=lifespan)


# 非同步 chunk 上傳任務
def upload_chunks_async(credentials: object) -> None:
    try:
        print(f'credentials: {credentials}')
    except Exception as e:
        print('❌ chunk 上傳失敗：', e)


# 記憶體儲存暫存的用戶設定（正式環境可用 DB/session 儲存）
oauth_state = {}


# --- /authorize-gmail ---
class GmailOAuthRequest(BaseModel):
    client_id: str
    client_secret: str


@app.post('/authorize-gmail')
def authorize_gmail(data: GmailOAuthRequest) -> dict:
    redirect_uri = 'http://localhost:8000/gmail-callback'
    client_config = {
        'installed': {
            'client_id': data.client_id,
            'client_secret': data.client_secret,
            'redirect_uris': [redirect_uri],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
        }
    }

    # 建立 Flow
    flow = Flow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )
    flow.redirect_uri = redirect_uri

    # 儲存這個 flow 的 config 以便之後 callback 用
    oauth_state['client_config'] = client_config
    oauth_state['redirect_uri'] = redirect_uri

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    return {'auth_url': auth_url}


# --- /gmail-callback ---
@app.get('/gmail-callback')
def gmail_callback(code: str, background_tasks: BackgroundTasks) -> dict:
    if 'client_config' not in oauth_state:
        return JSONResponse(
            status_code=400,
            content={'error': '未找到授權前的 config，請重新授權 /authorize-gmail'},
        )

    client_config = oauth_state['client_config']
    redirect_uri = oauth_state['redirect_uri']

    # 建立 Flow 並填入 code 換 token
    flow = Flow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )
    flow.redirect_uri = redirect_uri

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        background_tasks.add_task(upload_chunks_async, credentials)

        html_content = (
            '<html>\n'
            '<head>\n'
            '<title>匯入完成</title>\n'
            '</head>\n'
            '<body style="font-family: sans-serif;'
            ' text-align: center; margin-top: 100px;">\n'
            '<h1>✅ 匯入成功</h1>\n'
            '<p>信件已成功匯入記憶庫！</p>\n'
            '<p>你可以關閉這個視窗，回到 <b>MyDrift</b> 查看資料。</p>\n'
            '</body>\n'
            '</html>\n'
        )

        return HTMLResponse(content=html_content, status_code=200)

        # 建立 Gmail 服務物件
        # service = build('gmail', 'v1', credentials=credentials)
        # results = service.users().messages().list(userId='me', maxResults=5).execute()
        # messages = results.get('messages', [])
        # print('?????')
        # print(messages)

        # return {
        #     'message': '✅ 授權成功，這是你最近 5 封信的 ID',
        #     'messages': messages,
        #     'token_info': {
        #         'access_token': credentials.token,
        #         'refresh_token': credentials.refresh_token,
        #         'expires_in': credentials.expiry.isoformat(),
        #     },
        # }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': f'授權流程失敗：{str(e)}'},
        )


async def chat_stream_response(
    message: str,
    llm_name: str,
    llm_source: str,
    api_key: str | None,
    user_name: str | None,
) -> AsyncGenerator[str, None]:
    async with async_qdrant_client() as client:
        llm_handler = LLMHandler(
            llm_name=llm_name, llm_source=llm_source, api_key=api_key
        )
        llm_chat_func = llm_handler.get_llm_chat_func()

        agent_handler = AgentHandler(
            user_name=user_name,
            qdrant_client=client,
            embedding_model=app.state.embedding_model,
            llm_chat_func=llm_chat_func,
        )
        response = agent_handler.get_chat_response(message=message)
        async for token in response:
            yield token


async def reindex_stream_response(documents: list[dict]) -> AsyncGenerator[int, None]:
    handler = ReindexHandler(
        documents=documents,
        embedding_model=app.state.embedding_model,
        window_sizes=[5],
        stride=3,
    )
    response = handler.index_message_chunks()
    async for indexed_doc_count in response:
        yield (
            json.dumps(
                {
                    'status': 'ok',
                    'total_doc_count': len(documents),
                    'indexed_doc_count': indexed_doc_count,
                }
            )
            + '\n'
        )


@app.post('/chat')
async def chat_with_agent(request: MessagePayload) -> dict:
    return StreamingResponse(
        chat_stream_response(
            message=request.message,
            llm_name=request.llm_name,
            llm_source=request.llm_source,
            api_key=request.api_key,
            user_name=request.user_name,
        ),
        media_type='text/plain',
    )


@app.post('/upload-json')
async def upload_json(payload: UploadJsonPayload) -> dict:
    documents = payload.documents

    return StreamingResponse(
        reindex_stream_response(documents), media_type='text/plain'
    )


@app.get('/get-paginated-docs')
async def get_paginated_docs(page: int, page_size: int, senders: str = '') -> dict:
    async with async_mongodb_client() as client:
        return await ChatDoc.scroll(
            client=client, page=page, page_size=page_size, senders=senders
        )


@app.get('/get-page-count')
async def get_page_count(page_size: int = 3, senders: str = '') -> dict:
    async with async_mongodb_client() as client:
        return {
            'total_pages': await ChatDoc.get_page_count(
                client=client, page_size=page_size, senders=senders
            )
        }


@app.get('/health_check')
def health_check() -> None:
    return {'message': 'Hello, FastAPI! Bonjur!'}
