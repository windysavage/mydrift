import json

import streamlit as st

st.set_page_config(page_title='MyDrift', layout='wide')

st.title('🧠 MyDrift：個人對話記憶庫')

st.markdown('上傳你的對話記錄來開始探索你的記憶！')

# 匯入 JSON 訊息記錄
uploaded_file = st.file_uploader('上傳訊息 JSON 檔案', type=['json'])

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        st.success('載入成功 ✅')

        st.subheader('📄 預覽內容')
        st.json(data if isinstance(data, dict) else data[:3])  # 預覽前 3 筆

    except Exception as e:
        st.error(f'讀取 JSON 發生錯誤：{e}')

# 可加入手動重建記憶庫按鈕
if st.button('🔄 重新整理記憶庫'):
    st.info('這裡可以觸發後端邏輯來更新記憶索引（例如用 API 呼叫）')
