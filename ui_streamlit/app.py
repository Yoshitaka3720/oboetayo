# ui_streamlit/app.py

import streamlit as st
import json
from streamlit_lottie import st_lottie
from core.ai import AI
from gtts import gTTS
from io import BytesIO
import base64

def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

st.set_page_config(page_title="オボエタヨ", page_icon="🧠", layout="centered")
st.title("オボエタヨ Streamlit版")

# --- AI インスタンスをセッションステートで管理 ---
if "ai" not in st.session_state:
    st.session_state.ai = AI()

# --- 自発発話（セルフトーク）を pull_events() で取得してログに追加 ---
events = st.session_state.ai.pull_events()
for etype, msg in events:
    if etype == "self_talk":
        if "log" not in st.session_state:
            st.session_state["log"] = ""
        st.session_state["log"] += f"オボエタヨ：{msg}\n"
        st.rerun()

# --- Lottie アニメーション表示 ---
ai = st.session_state.ai
lottie_files = {
    "happy": load_lottiefile("assets/happy.json"),
    "neutral": load_lottiefile("assets/neutral.json"),
    "tired": load_lottiefile("assets/tired.json"),
}
avatar_placeholder = st.empty()
with avatar_placeholder:
    st_lottie(lottie_files.get(ai.mood, lottie_files["neutral"]), height=300)

# --- チャットログ初期化 ---
if "log" not in st.session_state:
    st.session_state["log"] = ""

# --- チャットフォーム ---
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("あなたのメッセージ", key="input")
    submitted  = st.form_submit_button("送信")
    if submitted and user_input:
        # 学習＆応答取得
        response = ai.learn(user_input)
        st.session_state["log"] += f"あなた：{user_input}\nオボエタヨ：{response}\n"
        st.session_state["input"] = ""

        # gTTS で音声合成して自動再生
        tts = gTTS(response, lang="ja")
        buf = BytesIO()
        tts.write_to_fp(buf)
        audio_bytes = buf.getvalue()
        b64 = base64.b64encode(audio_bytes).decode()
        audio_html = (
            '<audio autoplay src="data:audio/mp3;base64,'
            + b64 +
            '"></audio>'
        )
        st.markdown(audio_html, unsafe_allow_html=True)

        # アバター再描画
        avatar_placeholder.empty()
        with avatar_placeholder:
            st_lottie(lottie_files.get(ai.mood, lottie_files["neutral"]), height=300)

# --- ログ表示 ---
st.text_area("チャットログ", st.session_state["log"], height=300)
