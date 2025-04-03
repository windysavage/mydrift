import asyncio
import json

import httpx
import streamlit as st

# 頁面設定
st.set_page_config(page_title='MyDrift', layout='wide')
st.title('🧠 MyDrift：個人對話記憶庫')

# --- 🔧 側邊欄設定 ---
st.sidebar.header('設定')

# 📂 檔案上傳區（放進側邊欄）
st.sidebar.subheader('📤 上傳 JSON 檔案')
uploaded_files = st.sidebar.file_uploader(
    '選擇 JSON 檔案（可多選）', type=['json'], accept_multiple_files=True
)

if uploaded_files and st.sidebar.button('📨 傳送至後端'):
    data = []

    for file in uploaded_files:
        try:
            content = json.load(file)
            data.append(content)
        except Exception as e:
            st.sidebar.error(f'{file.name} 解析失敗：{e}')

    if data:
        response = httpx.post(
            'http://api:8000/upload-json', json={'memory_name': 'my_memory', 'documents': data}
        )
        if response.status_code == 200:
            st.sidebar.success('✅ 傳送成功')
            st.sidebar.json(response.json())
        else:
            st.sidebar.error(f'❌ 後端錯誤：{response.status_code}')

# 🔄 Refresh 記憶庫按鈕
st.sidebar.subheader('🔄 重建記憶索引')
if st.sidebar.button('重新整理記憶庫'):
    # TODO: 呼叫 API 重建記憶索引
    pass
    st.sidebar.info('已觸發記憶庫重建（等待 API 回應）')

# --- 💬 ChatGPT 風格問答介面 ---
st.subheader('🔍 問答查詢')

# 初始化聊天記錄
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

# 使用者輸入
user_input = st.chat_input('輸入你的問題...')

if user_input:
    # 顯示使用者輸入
    st.session_state.messages.append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # 建立空白區塊來更新逐字輸出
    with st.chat_message('assistant'):
        msg_placeholder = st.empty()

        async def get_streaming_reply(message: str) -> str:
            url = 'http://api:8000/chat'  # ✅ 請根據你的 API URL 調整
            reply = ''
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    'POST', url, json={'message': message}, timeout=30
                ) as resp:
                    async for chunk in resp.aiter_text():
                        reply += chunk
                        msg_placeholder.markdown(reply + '▌')
            msg_placeholder.markdown(reply)  # 最終清除游標
            return reply

        # 執行 async stream 回覆並取得最終內容
        final_response = asyncio.run(get_streaming_reply(user_input))

    # 儲存 assistant 回覆
    st.session_state.messages.append({'role': 'assistant', 'content': final_response})
