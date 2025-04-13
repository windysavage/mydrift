import logging

from fastapi import APIRouter, Request
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

    flow = Flow.from_client_config(
        client_config,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )
    flow.redirect_uri = redirect_uri

    request.app.state.client_config = client_config
    request.app.state.redirect_uri = redirect_uri

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    return {'auth_url': auth_url}


@auth_router.get('/gmail-callback')
def gmail_callback(code: str, request: Request) -> dict:
    if not request.app.state.client_config:
        return JSONResponse(
            status_code=400,
            content={
                'error': (
                    'Missing pre-authorization config. '
                    'Please re-authorize via /authorize-gmail.'
                )
            },
        )

    flow = Flow.from_client_config(
        request.app.state.client_config,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )
    flow.redirect_uri = request.app.state.redirect_uri

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        request.app.state.credentials_dict = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
        }

        html_content = (
            '<html>\n'
            '<head>\n'
            '<title>Authorization Complete</title>\n'
            '</head>\n'
            '<body style="font-family: sans-serif; '
            'text-align: center; margin-top: 100px;">\n'
            '<h1>✅ Authorization Successful</h1>\n'
            '<p>You have successfully granted access to your Gmail account.</p>\n'
            '<p>You can now start importing your emails into <b>MyDrift</b>.</p>\n'
            '<p>You may close this window.</p>\n'
            '</body>\n'
            '</html>\n'
        )

        return HTMLResponse(content=html_content, status_code=200)

    except GoogleAuthError as google_auth_error:
        logging.exception('Failed to exchange token during OAuth')
        return JSONResponse(
            status_code=400,
            content={
                'error': f'Google OAuth authorization error: {str(google_auth_error)}'
            },
        )
    except Exception as e:
        logging.exception('Exception occurred during gmail-callback')
        return JSONResponse(
            status_code=500,
            content={'error': f'Authorization process failed: {str(e)}'},
        )


@auth_router.post('/get-auth-status')
def get_auth_status(request: Request) -> dict:
    credentials = getattr(request.app.state, 'credentials_dict', None)
    if credentials:
        return {'authorized': True}
    return {'authorized': False}
