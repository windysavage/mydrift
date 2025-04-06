import asyncio
import json
from datetime import UTC, datetime, timedelta, timezone

import httpx
import streamlit as st

# 頁面設定
st.set_page_config(page_title='MyDrift', layout='wide')
st.title('🧠 MyDrift：個人對話記憶庫')

# 建立 Tabs
chat_tab, import_tab, view_tab = st.tabs(
    ['💬 聊天介面', '📤 匯入資料', '📚 記憶庫資料']
)

# --- 📤 匯入資料分頁 ---
with import_tab:
    st.header('📤 匯入 JSON 檔案')

    uploaded_files = st.file_uploader(
        '選擇 JSON 檔案（可多選）', type=['json'], accept_multiple_files=True
    )

    async def send_to_backend_and_stream(data: list[dict]) -> None:
        progress = st.progress(0)
        status_text = st.empty()

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    'POST',
                    'http://api:8000/upload-json',
                    json={'documents': data},
                    timeout=1200,
                ) as resp:
                    total = 1
                    indexed = 0

                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            info = json.loads(line)
                            total = info.get('total_doc_count', total)
                            indexed = info.get('indexed_doc_count', indexed)
                            percent = min(int((indexed / total) * 100), 100)

                            status_text.markdown(
                                f'📄 已建立索引：{indexed}/{total} 筆文件'
                            )
                            progress.progress(percent)
                        except Exception as e:
                            st.warning(f'無法解析回應：{line} ({e})')
                    st.success('✅ 索引重建完成')
            except Exception as e:
                st.error(f'❌ 傳送過程失敗：{e}')

    if uploaded_files and st.button('📨 傳送至後端並建立索引'):
        docs = []
        for f in uploaded_files:
            try:
                content = json.load(f)
                docs.append(content)
            except Exception as e:
                st.error(f'{f.name} 解析失敗：{e}')

        if docs:
            asyncio.run(send_to_backend_and_stream(docs))

# --- 💬 聊天介面分頁 ---
with chat_tab:
    st.header('🔍 問答查詢')

    # 模型設定區塊
    with st.expander('⚙️ 模型設定', expanded=False):
        st.session_state.user_name = st.text_input(
            '🧑 我的名字', placeholder='輸入你在對話中的名字'
        )

        st.session_state.llm_source = st.selectbox(
            '選擇模型來源', options=['openai', 'ollama'], index=0
        )

        if st.session_state.llm_source == 'openai':
            st.session_state.llm_name = st.selectbox(
                '選擇模型名稱', options=['gpt-3.5-turbo', 'gpt-4'], index=0
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
                    st.warning('⚠️ 無法取得 Ollama 模型清單')
            except Exception as e:
                available_models = []
                st.warning(f'⚠️ 錯誤：無法連線至 Ollama：{e}')

            if available_models:
                st.session_state.llm_name = st.selectbox(
                    '選擇模型名稱', options=available_models, index=0
                )
            else:
                st.session_state.llm_name = st.text_input(
                    '輸入模型名稱（未列出）', placeholder='例如：llama3'
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

    user_input = st.chat_input('輸入你的問題...')

    if user_input:
        st.session_state.messages.append({'role': 'user', 'content': user_input})

        with scrollable_chat.chat_message('user'):
            st.markdown(user_input)

        with scrollable_chat.chat_message('assistant'):
            msg_placeholder = st.empty()

            async def get_streaming_reply(message: str) -> str:
                url = 'http://api:8000/chat'
                payload = {
                    'message': message,
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
    st.header('📚 記憶庫資料預覽')

    page_size = 3

    sender_filter = st.text_input(
        '🔍 篩選發言者（使用 , 分隔，例如：王小明,王小花）', value=''
    )

    if 'doc_current_page' not in st.session_state:
        st.session_state.doc_current_page = 1
    if 'doc_chunks' not in st.session_state:
        st.session_state.doc_chunks = []

    search_button = st.button('🔍 查詢')

    def fetch_page_data(page: int) -> None:
        try:
            params = {'page': page, 'page_size': page_size}
            if sender_filter.strip():
                params['senders'] = sender_filter

            resp = httpx.get(
                'http://api:8000/get-paginated-docs',
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.doc_chunks = data.get('chunks', [])
                st.session_state.doc_current_page = data.get('page', page)
            else:
                st.session_state.doc_chunks = []
                st.error(f'❌ API 回傳錯誤：{resp.status_code}')
        except Exception as e:
            st.session_state.doc_chunks = []
            st.error(f'❌ 發生錯誤：{e}')

    def fetch_page_count() -> None:
        try:
            params = {}
            if sender_filter.strip():
                params['senders'] = sender_filter

            resp = httpx.get(
                'http://api:8000/get-page-count',
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.doc_total_pages = data.get('total_pages', 1)
            else:
                st.error(f'❌ API 回傳錯誤：{resp.status_code}')
        except Exception as e:
            st.error(f'❌ 發生錯誤：{e}')

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
            format_func=lambda x: f'第 {x} 頁',
        )

        if page_selection != current_page:
            st.session_state.doc_current_page = page_selection
            fetch_page_data(page_selection)
            st.rerun()

        for idx, chunk in enumerate(chunks):
            with st.expander(f'🧾 片段 {idx + 1}', expanded=True):
                st.markdown(
                    f'**起始時間**: {format_ts(chunk.get("start_timestamp", "N/A"))}'
                )
                st.markdown(
                    f'**結束時間**: {format_ts(chunk.get("end_timestamp", "N/A"))}'
                )
                st.markdown(f'**發言者**: {", ".join(chunk.get("senders", []))}')
                st.code(chunk.get('text', ''), language='text')
    else:
        st.info('請先輸入發言者並點選「查詢」')
