import asyncio
import json
from datetime import UTC, datetime, timedelta, timezone

import httpx
import streamlit as st

from settings import get_settings

# 頁面設定
st.set_page_config(page_title='MyDrift', layout='wide')
st.title('🧠 MyDrift: Personal Conversation Memory System')

# 建立 Tabs
chat_tab, import_tab, view_tab = st.tabs(
    ['💬 Chat Interface', '📤 Import Data', '📚 Memory Data']
)
# --- 📤 匯入資料分頁 ---
with import_tab:
    st.subheader('📤 Import JSON Files')

    uploaded_files = st.file_uploader(
        'Select JSON files (multiple selection allowed)',
        type=['json'],
        accept_multiple_files=True,
    )

    async def send_to_backend_and_stream(data: list[dict]) -> None:
        progress = st.progress(0)
        status_text = st.empty()

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    'POST',
                    'http://api:8000/ingest/message',
                    json={'documents': data},
                    timeout=1200,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            info = json.loads(line)
                            ratio = info.get('indexed_ratio', 0)
                            percent = int(ratio * 100)
                            progress.progress(percent)
                            status_text.markdown(f'🚀 Completed: {percent}%')
                        except Exception as e:
                            st.warning(f'Unable to parse response: {line} ({e})')
                    st.success('✅ Indexing completed')
            except Exception as e:
                st.error(f'❌ Sending failed: {e}')

    if uploaded_files and st.button('📨 Send to Backend and Index'):
        docs = []
        for f in uploaded_files:
            try:
                content = json.load(f)
                docs.append(content)
            except Exception as e:
                st.error(f'{f.name} Parsing failed: {e}')

        if docs:
            asyncio.run(send_to_backend_and_stream(docs))

    # ------------- Gmail 授權與導入區塊 -------------
    st.markdown('---')
    st.subheader('📧 Authorize Gmail Connection')

    # 顯示授權按鈕
    if st.button('🔐 Start Gmail Authorization'):
        try:
            resp = httpx.post(
                'http://api:8000/auth/authorize-gmail',
                json={
                    'client_id': get_settings().GOOGLE_CLIENT_ID,
                    'client_secret': get_settings().GOOGLE_CLIENT_SECRET,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                auth_url = resp.json().get('auth_url')
                st.success(
                    '✅ Authorization link created. Click the button below to continue.'
                )
                st.markdown(
                    f'<a href="{auth_url}" target="_blank" '
                    f'style="font-size: 1.1em; text-decoration: none;">'
                    '👉 Go to Google Authorization Page'
                    '</a>',
                    unsafe_allow_html=True,
                )
            else:
                st.error(f'❌ Backend error: {resp.status_code} {resp.text}')
        except Exception as e:
            st.error(f'❌ Cannot connect to backend: {e}')

    st.markdown('---')
    st.subheader('📥 Import Authorized Gmail to Memory')

    if st.button('🚀 Start Importing Emails'):
        progress_bar = st.progress(0, text='Starting import...')
        status_text = st.empty()

        try:
            with httpx.stream(
                'POST', 'http://api:8000/ingest/gmail', timeout=None
            ) as response:
                if response.status_code != 200:
                    st.error(
                        f'❌ Import failed: {response.status_code} {response.text}'
                    )
                else:
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                ratio = data.get('indexed_ratio', 0)
                                percent = int(ratio * 100)
                                progress_bar.progress(
                                    percent, text=f'Importing... {percent}%'
                                )
                                status_text.text(f'{percent}% completed')
                            except json.JSONDecodeError:
                                st.warning('⚠️ Received malformed line from stream.')
            st.success('✅ Import completed!')
        except Exception as e:
            st.error(f'❌ Failed to start import: {e}')


# --- 💬 聊天介面分頁 ---
with chat_tab:
    st.header('🔍 Query and Answer')

    # 模型設定區塊
    with st.expander('⚙️ Model Settings', expanded=False):
        st.session_state.user_name = st.text_input(
            '🧑 My Name', placeholder='Enter your name in the conversation'
        )

        st.session_state.llm_source = st.selectbox(
            'Select Model Source', options=['openai', 'ollama'], index=0
        )

        if st.session_state.llm_source == 'openai':
            st.session_state.llm_name = st.selectbox(
                'Select Model Name', options=['gpt-3.5-turbo', 'gpt-4'], index=0
            )
            st.session_state.api_key = st.text_input(
                'OpenAI API Key', type='password', placeholder='sk-...'
            )
        elif st.session_state.llm_source == 'ollama':
            try:
                response = httpx.get(
                    'http://host.docker.internal:11434/api/tags', timeout=5
                )
                if response.status_code == 200:
                    models_data = response.json().get('models', [])
                    available_models = [m['name'] for m in models_data]
                else:
                    available_models = []
                    st.warning('⚠️ Unable to retrieve Ollama model list')
            except Exception as e:
                available_models = []
                st.warning(f'⚠️ Error: Unable to connect to Ollama: {e}')

            if available_models:
                st.session_state.llm_name = st.selectbox(
                    'Select Model Name', options=available_models, index=0
                )
            else:
                st.session_state.llm_name = st.text_input(
                    'Enter Model Name (not listed)', placeholder='e.g., llama3'
                )

            st.session_state.api_key = None

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    scrollable_chat = st.container()
    with scrollable_chat:
        st.markdown(
            """
            <div style="max-height: 500px; overflow-y: auto; padding-right: 10px;" 
            id="chat-box">
        """,
            unsafe_allow_html=True,
        )

        for msg in st.session_state.messages:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

        st.markdown("""</div>""", unsafe_allow_html=True)

    user_input = st.chat_input('Enter your question...')

    if user_input:
        st.session_state.messages.append({'role': 'user', 'content': user_input})

        with scrollable_chat.chat_message('user'):
            st.markdown(user_input)

        with scrollable_chat.chat_message('assistant'):
            msg_placeholder = st.empty()

            async def get_streaming_reply(message: str) -> str:
                url = 'http://api:8000/chat/chat-with-agent'
                payload = {
                    'message': message,
                    'history': st.session_state.messages,
                    'llm_source': st.session_state.llm_source,
                    'llm_name': st.session_state.llm_name,
                    'api_key': st.session_state.api_key,
                    'user_name': st.session_state.user_name,
                }
                if st.session_state.api_key:
                    payload['api_key'] = st.session_state.api_key

                reply = ''
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        'POST', url, json=payload, timeout=30
                    ) as resp:
                        async for chunk in resp.aiter_text():
                            reply += chunk
                            msg_placeholder.markdown(reply + '▌')
                msg_placeholder.markdown(reply)
                return reply

            final_response = asyncio.run(get_streaming_reply(user_input))

        st.session_state.messages.append(
            {'role': 'assistant', 'content': final_response}
        )


# --- 📚 記憶庫資料分頁 ---
def format_ts(ts_ms: int) -> str:
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
        dt_utc8 = dt.astimezone(timezone(timedelta(hours=8)))
        return dt_utc8.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return 'N/A'


with view_tab:
    st.header('📚 Memory Data Preview')

    page_size = 3

    sender_filter = st.text_input(
        '🔍 Filter by Sender (separate with commas, e.g., Alice,Bob)', value=''
    )

    if 'doc_current_page' not in st.session_state:
        st.session_state.doc_current_page = 1
    if 'doc_chunks' not in st.session_state:
        st.session_state.doc_chunks = []

    search_button = st.button('🔍 Search')

    def fetch_page_data(page: int) -> None:
        try:
            params = {'page': page, 'page_size': page_size}
            if sender_filter.strip():
                params['senders'] = sender_filter

            resp = httpx.get(
                'http://api:8000/memory/get-paginated-docs',
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.doc_chunks = data.get('chunks', [])
                st.session_state.doc_current_page = data.get('page', page)
            else:
                st.session_state.doc_chunks = []
                st.error(f'❌ API returned error: {resp.status_code}')
        except Exception as e:
            st.session_state.doc_chunks = []
            st.error(f'❌ Error occurred: {e}')

    def fetch_page_count() -> None:
        try:
            params = {}
            if sender_filter.strip():
                params['senders'] = sender_filter

            resp = httpx.get(
                'http://api:8000/memory/get-page-count',
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.doc_total_pages = data.get('total_pages', 1)
            else:
                st.error(f'❌ API returned error: {resp.status_code}')
        except Exception as e:
            st.error(f'❌ Error occurred: {e}')

    if search_button:
        fetch_page_data(1)
        fetch_page_count()

    chunks = st.session_state.doc_chunks
    if chunks:
        total_pages = st.session_state.doc_total_pages
        current_page = st.session_state.doc_current_page

        page_selection = st.selectbox(
            '',
            options=list(range(1, total_pages + 1)),
            index=current_page - 1,
            format_func=lambda x: f'Page {x}',
        )

        if page_selection != current_page:
            st.session_state.doc_current_page = page_selection
            fetch_page_data(page_selection)
            st.rerun()

        for idx, chunk in enumerate(chunks):
            with st.expander(f'🧾 Chunk {idx + 1}', expanded=True):
                st.markdown(
                    f'**Start Time**: {format_ts(chunk.get("start_timestamp", "N/A"))}'
                )
                st.markdown(
                    f'**End Time**: {format_ts(chunk.get("end_timestamp", "N/A"))}'
                )
                st.markdown(f'**Senders**: {", ".join(chunk.get("senders", []))}')
                st.code(chunk.get('text', ''), language='text')
    else:
        st.info('Please enter a sender and click "Search"')
