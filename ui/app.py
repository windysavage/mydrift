import asyncio
import os

import httpx
import streamlit as st

# 頁面設定
st.set_page_config(page_title='MyDrift', layout='wide')
st.title('🧠 MyDrift：個人對話記憶庫')

# --- 🔧 側邊欄設定 ---
st.sidebar.header('設定')

# 📂 選擇資料來源資料夾
default_base_dir = os.path.expanduser('/app')

st.sidebar.subheader('📂 選擇資料來源資料夾')
selected_folder = None
selected_path = None

if os.path.exists(default_base_dir):
    folders = sorted(
        [
            f
            for f in os.listdir(default_base_dir)
            if os.path.isdir(os.path.join(default_base_dir, f))
        ]
    )

    if folders:
        selected_folder = st.sidebar.selectbox('選擇子資料夾', [''] + folders)
        if selected_folder:
            selected_path = os.path.join(default_base_dir, selected_folder)
            st.sidebar.markdown(f'✅ **你選擇的資料夾：** `{selected_path}`')

            if st.sidebar.button('設定資料夾'):
                # TODO: 呼叫 API 設定資料夾
                pass
                st.sidebar.success(f'已設定資料夾：{selected_path}')
        else:
            st.sidebar.info('請從上方選擇一個資料夾')
    else:
        st.sidebar.warning(f'`{default_base_dir}` 沒有任何資料夾')
else:
    st.sidebar.error(f'❌ 找不到預設目錄：{default_base_dir}')

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
