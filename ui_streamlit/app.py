#app.py

# --- 標準ライブラリ ---
import io
import time
import json
import base64
from datetime import datetime
from io import BytesIO

# --- サードパーティ ---
import streamlit as st
from streamlit_lottie import st_lottie
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av
from gtts import gTTS
from pydub import AudioSegment
import numpy as np

# --- 自作モジュール ---
from core.ai import AI

# --- Lottieファイル読み込みユーティリティ ---
def load_lottiefile(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# --- ページ設定 ---
st.set_page_config(page_title="オボエタヨ", page_icon="🧠", layout="centered")
st.title("オボエタヨ Streamlit版")

# --- AI & Lottie読み込み ---
ai = AI()
lottie_files = {
    mood: load_lottiefile(f"lottie_assets/{mood}.json")
    for mood in ("happy", "neutral", "tired")
}

# --- アバター表示 ---
avatar_placeholder = st.empty()
with avatar_placeholder:
    st_lottie(lottie_files.get(ai.mood), height=300, loop=False)

# --- マイク波形メーター準備 ---
if "vol" not in st.session_state:
    st.session_state["vol"] = 0.0

# デバッグ用 VolumeMeter
class VolumeMeter(AudioProcessorBase):
    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        # デバッグ: 呼び出し確認
        print("recv_audio called")
        # PCMサンプル取得
        pcm = frame.to_ndarray().flatten()
        # デバッグ: PCM情報確認
        print(f"pcm size: {pcm.size}, dtype: {pcm.dtype}")
        # 音量計算 (正規化)
        try:
            vol_value = np.linalg.norm(pcm) / 3000.0
        except Exception as e:
            print(f"Error computing norm: {e}")
            vol_value = 0.0
        vol = min(vol_value, 1.0)
        st.session_state["vol"] = vol
        return frame

# --- サイドバーで webrtc を開始 ---
with st.sidebar:
    st.markdown("### 🎤 マイク波形")
    # 波形バー用プレースホルダー
    waveform_placeholder = st.empty()
    st.write("")  # 余白
    webrtc_streamer(
        key="mic",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=VolumeMeter,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
        sendback_audio=False
    )

# --- プレースホルダーを使って波形バーを描画 ---
vol = int(st.session_state.get("vol", 0.0) * 100)
waveform_placeholder.progress(vol)

# --- チャットログ用ステート初期化 ---
if "log" not in st.session_state:
    st.session_state["log"] = ""
if "last_input" not in st.session_state:
    st.session_state["last_input"] = None

# --- チャットフォーム ---
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("あなたのメッセージ", key="input")
    submitted = st.form_submit_button("送信")

    if submitted and user_input:
        # 連呼検出と代替リアクション
        if user_input == st.session_state["last_input"]:
            alt_responses = [
                "同じことを繰り返さないでください…",
                "もう言いましたよね？",
                "しつこいですねー…",
            ]
            response = np.random.choice(alt_responses)
        else:
            response = ai.learn(user_input)
        st.session_state["last_input"] = user_input

        # ログ更新
        st.session_state["log"] += f"あなた: {user_input}\nオボエタヨ: {response}\n"

        # gTTSで音声合成
        tts = gTTS(response, lang="ja")
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_bytes = buf.getvalue()

        # TTS時の波形バー表示
        try:
            sound = AudioSegment.from_file(buf, format="mp3")
            samples = np.array(sound.get_array_of_samples()).astype(np.float32)
            rms = np.sqrt(np.mean(samples ** 2))
            level = int(min(rms / 1000 * 100, 100))
        except Exception:
            level = 0
        waveform_placeholder.progress(level)
        time.sleep(1)
        waveform_placeholder.empty()

        # TTS自動再生
        b64 = base64.b64encode(audio_bytes).decode()
        audio_html = '<audio autoplay src="data:audio/mp3;base64,' + b64 + '"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)

        # メッセージ送信後、アバターを再表示
        avatar_placeholder.empty()
        with avatar_placeholder:
            st_lottie(lottie_files.get(ai.mood), height=300, loop=False)

# --- チャットログ表示 ---
st.text_area("チャットログ", st.session_state["log"], height=300)
