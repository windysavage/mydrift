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

    # 📂 檔案上傳區
    uploaded_files = st.file_uploader(
        '選擇 JSON 檔案（可多選）', type=['json'], accept_multiple_files=True
    )

    if uploaded_files and st.button('📨 傳送至後端'):
        data = []

        for file in uploaded_files:
            try:
                content = json.load(file)
                data.append(content)
            except Exception as e:
                st.error(f'{file.name} 解析失敗：{e}')

        if data:
            response = httpx.post(
                'http://api:8000/upload-json',
                json={'memory_name': 'my_memory', 'documents': data},
            )
            if response.status_code == 200:
                st.success('✅ 傳送成功')
                st.json(response.json())
            else:
                st.error(f'❌ 後端錯誤：{response.status_code}')

    # 🔄 Refresh 記憶庫按鈕
    if st.button('🔄 重新整理記憶庫'):
        # TODO: 呼叫 API 重建記憶索引
        st.info('已觸發記憶庫重建（等待 API 回應）')

# --- 💬 聊天介面分頁 ---
with chat_tab:
    st.header('🔍 問答查詢')

    # 初始化聊天記錄
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # 聊天訊息顯示區（限制高度並可滾動）
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

    # 🧾 使用者輸入區（固定在最下方）
    user_input = st.chat_input('輸入你的問題...')

    if user_input:
        st.session_state.messages.append({'role': 'user', 'content': user_input})

        with scrollable_chat.chat_message('user'):
            st.markdown(user_input)

        with scrollable_chat.chat_message('assistant'):
            msg_placeholder = st.empty()

            async def get_streaming_reply(message: str) -> str:
                url = 'http://api:8000/chat'
                reply = ''
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        'POST', url, json={'message': message}, timeout=30
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

    if 'doc_current_page' not in st.session_state:
        st.session_state.doc_current_page = 1
    if 'doc_total_pages' not in st.session_state:
        st.session_state.doc_total_pages = 1
    if 'doc_chunks' not in st.session_state:
        st.session_state.doc_chunks = []

    def fetch_page_data(page: int) -> None:
        try:
            resp = httpx.get(
                'http://api:8000/get-docs',
                params={'page': page, 'page_size': page_size},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.doc_chunks = data.get('chunks', [])
                st.session_state.doc_current_page = data.get('page', page)
                st.session_state.doc_total_pages = data.get('total_pages', 1)
            else:
                st.error(f'❌ API 回傳錯誤：{resp.status_code}')
        except Exception as e:
            st.error(f'❌ 發生錯誤：{e}')

    # 初始載入
    if not st.session_state.doc_chunks:
        fetch_page_data(st.session_state.doc_current_page)

    # 🔽 頁碼選單
    total_pages = st.session_state.doc_total_pages
    current_page = st.session_state.doc_current_page

    page_selection = st.selectbox(
        '',
        options=list(range(1, total_pages + 1)),
        index=current_page - 1,
        format_func=lambda x: f'第 {x} 頁',
    )

    if page_selection != current_page:
        fetch_page_data(page_selection)
        st.rerun()

    # 顯示 chunk 資訊
    chunks = st.session_state.doc_chunks
    for idx, chunk in enumerate(chunks):
        with st.expander(f'🧾 片段 {idx + 1}', expanded=True):
            st.markdown(
                f'**起始時間**: {format_ts(chunk.get("start_timestamp", "N/A"))}'
            )
            st.markdown(f'**結束時間**: {format_ts(chunk.get("end_timestamp", "N/A"))}')
            st.markdown(f'**發言者**: {", ".join(chunk.get("senders", []))}')
            st.code(chunk.get('text', ''), language='text')
