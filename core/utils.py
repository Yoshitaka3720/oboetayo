import os
import io
import re
import platform
import subprocess
import threading

from PIL import Image, ImageSequence
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# —— テキスト正規化 ——
def normalize_text(text: str) -> str:
    """
    英数字・ひらがな・カタカナ・漢字以外を除去し、小文字化
    """
    return re.sub(r"[^0-9a-z\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", "", text.lower())

# —— GIF フレーム読み込み ——
def load_gif_frames(path: str, size: tuple[int,int]=None) -> list[bytes]:
    """
    PIL で GIF を開き、全フレームを PNG バイト列に変換して返却。
    size=(w,h) 指定でリサイズ。
    """
    frames: list[bytes] = []
    img = Image.open(path)
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("RGBA")
        if size is not None:
            # Pillow >=10 では ANTIALIAS 廃止 → LANCZOS を指定
            frame = frame.resize(size, resample=Image.LANCZOS)
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        frames.append(buf.getvalue())
    return frames

# —— TTS エンジン管理 ——
_tts_lock   = threading.Lock()
_tts_engine = None

def _get_engine():
    global _tts_engine
    with _tts_lock:
        if _tts_engine is None and pyttsx3 is not None:
            try:
                _tts_engine = pyttsx3.init()
            except Exception as e:
                print("[TTS init error]", e)
                _tts_engine = None
        return _tts_engine

def speak(text: str):
    """
    テキストを読み上げ。macOS なら say コマンドを優先し、
    失敗時／他 OS は pyttsx3 → フォールバック。
    """
    # まず macOS say
    if platform.system() == "Darwin":
        try:
            subprocess.Popen(["say", text])
            return
        except Exception as e:
            print("[say error]", e)
    # 次に pyttsx3
    engine = _get_engine()
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
            return
        except Exception as e:
            print("[TTS error]", e)
    # 最後に汎用フォールバック
    if platform.system() == "Darwin":
        subprocess.run(["say", text])
    elif platform.system().startswith("win"):
        # Windows の場合 PowerShell 経由で
        subprocess.run(["mshta", f"javascript:new ActiveXObject('SAPI.SpVoice').Speak('{text}');close()"])
    else:
        # Linux 等で espeak があれば
        subprocess.run(["espeak", text])
