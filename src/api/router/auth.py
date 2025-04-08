import logging

import requests
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
)
from google.auth.exceptions import GoogleAuthError
from google_auth_oauthlib.flow import Flow

from api.schema import (
    GmailOAuthPayload,
)

auth_router = APIRouter(prefix='/auth', tags=['auth'])


@auth_router.post('/authorize-gmail')
def authorize_gmail(data: GmailOAuthPayload, request: Request) -> dict:
    if not data.client_id or not data.client_secret:
        raise ValueError(
            'You should provide client_id and client_secret to enable authorization'
        )
    redirect_uri = 'http://localhost:8000/auth/gmail-callback'
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
    request.app.state.client_config = client_config
    request.app.state.redirect_uri = redirect_uri

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    return {'auth_url': auth_url}


@auth_router.get('/gmail-callback')
def gmail_callback(
    code: str, background_tasks: BackgroundTasks, request: Request
) -> dict:
    if not request.app.state.client_config:
        return JSONResponse(
            status_code=400,
            content={'error': '未找到授權前的 config，請重新授權 /authorize-gmail'},
        )

    # 建立 Flow 並填入 code 換 token
    flow = Flow.from_client_config(
        request.app.state.client_config,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )
    flow.redirect_uri = request.app.state.redirect_uri

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        background_tasks.add_task(
            requests.post,
            'http://localhost:8000/ingest/gmail',
            json={
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
            },
        )

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

    except GoogleAuthError as google_auth_error:
        logging.exception('OAuth 交換 token 失敗')
        return JSONResponse(
            status_code=400,
            content={'error': f'Google OAuth 授權錯誤：{str(google_auth_error)}'},
        )
    except Exception as e:
        logging.exception('gmail-callback 發生例外')
        return JSONResponse(
            status_code=500,
            content={'error': f'授權流程失敗：{str(e)}'},
        )
