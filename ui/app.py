import asyncio
import json

import httpx
import streamlit as st

# 頁面設定
st.set_page_config(page_title='MyDrift', layout='wide')
st.title('🧠 MyDrift：個人對話記憶庫')

# 建立 Tabs
chat_tab, import_tab, view_tab = st.tabs(['💬 聊天介面', '📤 匯入資料', '📚 記憶庫資料'])

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
                'http://api:8000/upload-json', json={'memory_name': 'my_memory', 'documents': data}
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
            <div style="max-height: 500px; overflow-y: auto; padding-right: 10px;" id="chat-box">
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

        st.session_state.messages.append({'role': 'assistant', 'content': final_response})

# --- 📚 記憶庫資料分頁 ---
with view_tab:
    st.header('📚 查看目前記憶庫內容')

    try:
        response = httpx.get('http://api:8000/memory/my_memory')
        if response.status_code == 200:
            documents = response.json().get('documents', [])
            st.success(f'✅ 共載入 {len(documents)} 筆資料')
            for doc in documents:
                with st.expander(doc.get('title', '(無標題)')):
                    st.json(doc)
        else:
            st.error(f'❌ 載入失敗：{response.status_code}')
    except Exception as e:
        st.error(f'❌ 發生錯誤：{e}')
