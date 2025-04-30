# gui.py
import os
import time
import threading

import PySimpleGUI as sg

from core.ai import AI
from core.utils import load_gif_frames, speak  # 🔥 ここ修正
from ui_pysimplegui import audio_meter  # 同ディレクトリに配置

# —— 定数設定（背景色） ——
BG_COLOR = {
    "happy":   "#ffe8f0",
    "neutral": "#f0f0f0",
    "tired":   "#dcdcdc",
}

# —— アセット設定 ——
BASE           = os.path.dirname(__file__)
ASSETS         = os.path.join(BASE, "assets")
GIF_SIZE       = (128, 128)
FRAME_INTERVAL = 0.2

# GIF フレーム読み込み
GIF_FRAMES = {
    mood: load_gif_frames(os.path.join(ASSETS, f"{mood}_talk.gif"), size=GIF_SIZE)
    for mood in ("happy", "neutral", "tired")
}

# —— レイアウト定義 ——
sg.theme("DarkBlue3")
layout = [
    [sg.Text("オボエタヨ", size=(40,1), font=("Helvetica",16), background_color=BG_COLOR["neutral"])],
    [sg.Image(key="-AVATAR-", size=GIF_SIZE), sg.Text("", key="-MOOD-", font=("Helvetica",14), background_color=BG_COLOR["neutral"])],
    # ここが波形メーター（音量バー）
    [sg.Text("音量：", background_color=BG_COLOR["neutral"]), sg.ProgressBar(100, orientation='h', size=(40,10), key='-METER-', bar_color=('green','gray'))],
    [sg.Multiline("", size=(60,20), key="-LOG-", autoscroll=True, disabled=True, background_color='#ffffff')],
    [sg.InputText("", size=(45,1), key="-INPUT-"),
     sg.Button("送信", bind_return_key=True), sg.Button("終了")]
]
window = sg.Window(
    "オボエタヨ GUI版",
    layout,
    background_color=BG_COLOR["neutral"],
    finalize=True
)
window.TKroot.minsize(600, 550)

# —— 波形メーター（音量バー）スレッド起動 ——
threading.Thread(target=audio_meter.start_meter, daemon=True).start()

# —— AI 初期化 ——
ai = AI()
ai.start_spontaneous(lambda msg: window.write_event_value("-SPONT-", msg))

# —— 初期表示 ——
window["-MOOD-"].update(f"[気分：{ai.mood}]")
window["-AVATAR-"].update(data=GIF_FRAMES[ai.mood][0])
window.TKroot.configure(bg=BG_COLOR.get(ai.mood, BG_COLOR["neutral"]))

# —— 状態変数 ——
last_think       = time.time()
gif_playing      = False
current_gif_mood = None
gif_frame_index  = 0
last_frame_time  = time.time()

# —— 補助関数 ——
def update_mood():
    window["-MOOD-"].update(f"[気分：{ai.mood}]")
    bg = BG_COLOR.get(ai.mood, BG_COLOR["neutral"])
    window.TKroot.configure(bg=bg)
    # テキスト要素も背景色を更新
    for key in ("-MOOD-",):
        window[key].update(background_color=bg)

def show_talk_gif(mood):
    global gif_playing, current_gif_mood, gif_frame_index, last_frame_time
    if mood in GIF_FRAMES:
        gif_playing      = True
        current_gif_mood = mood
        gif_frame_index  = 0
        last_frame_time  = time.time()
    else:
        gif_playing = False
        window["-AVATAR-"].update(data=GIF_FRAMES.get(mood, [b""])[0])

def typing_animation():
    for dots in ("…", "…", "…"):
        window["-LOG-"].update(f"オボエタヨ：{dots}\n", append=True)
        window.refresh()
        time.sleep(0.2)

def scroll_bottom():
    try:
        window["-LOG-"].Widget.yview_moveto(1.0)
    except Exception:
        pass

# —— メインループ ——
while True:
    event, values = window.read(timeout=50)
    now = time.time()

    # 0) 波形メーター更新
    vol = audio_meter.get_volume()
    if vol is not None:
        window['-METER-'].update(vol)

    # 1) think() ＋ 気分更新
    if event == sg.TIMEOUT_EVENT and now - last_think > 1.0:
        ai.think()
        last_think = now
        update_mood()
        if not gif_playing:
            window["-AVATAR-"].update(data=GIF_FRAMES[ai.mood][0])

    # 2) GIF 再生更新
    if gif_playing and current_gif_mood:
        if now - last_frame_time >= FRAME_INTERVAL:
            frames = GIF_FRAMES[current_gif_mood]
            window['-AVATAR-'].update(data=frames[gif_frame_index])
            gif_frame_index += 1
            last_frame_time = now
            if gif_frame_index >= len(frames):
                gif_playing     = False
                gif_frame_index = 0
                window['-AVATAR-'].update(data=frames[0])

    # 3) 自発発話イベント
    if event == "-SPONT-":
        msg = values[event]
        window["-LOG-"].update(f"オボエタヨ：{msg}\n", append=True)
        scroll_bottom()
        show_talk_gif(ai.mood)
        speak(msg)

    # 4) 送信
    if event == "送信":
        raw = values["-INPUT-"]
        window["-INPUT-"].update("")
        window["-LOG-"].update(f"あなた：{raw}\n", append=True)
        scroll_bottom()

        typing_animation()
        show_talk_gif(ai.mood)

        def worker(user_text):
            resp = ai.learn(user_text)
            window.write_event_value("-RESPONSE-", resp or "")
        threading.Thread(target=worker, args=(raw,), daemon=True).start()

    # 5) 応答完了
    if event == "-RESPONSE-":
        resp = values[event]
        window["-LOG-"].update(f"オボエタヨ：{resp}\n", append=True)
        scroll_bottom()
        show_talk_gif(ai.mood)
        speak(resp)

    # 6) 終了
    if event in (sg.WIN_CLOSED, "終了"):
        break

window.close()
