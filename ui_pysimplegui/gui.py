# ui_pysimplegui/gui.py

import PySimpleGUI as sg
import time
from queue import Empty
from core.ai import AI

sg.theme('LightGray1')

layout = [
    [sg.Text('オボエタヨ', size=(40, 1), font=('Helvetica', 16))],
    [sg.Image('', key='-AVATAR-', size=(100, 100)), sg.Text('', key='-MOOD-')],
    [sg.Multiline('', size=(60, 20), key='-LOG-', disabled=True, autoscroll=True)],
    [
        sg.InputText('', size=(45, 1), key='-INPUT-'),
        sg.Button('送信', bind_return_key=True),
        sg.Button('終了')
    ]
]

window = sg.Window('オボエタヨ', layout, finalize=True)
ai = AI()

while True:
    event, values = window.read(timeout=100)
    if event in (sg.WIN_CLOSED, '終了'):
        break

    # 独り言 (self_talk) イベントを pull_events() で取得してログに出力
    try:
        events = ai.pull_events()
        for etype, msg in events:
            if etype == "self_talk":
                window['-LOG-'].update(f"オボエタヨ：{msg}\n", append=True)
    except Empty:
        pass

    # ユーザーからの入力
    if event == '送信':
        user_input = values['-INPUT-'].strip()
        if user_input:
            response = ai.learn(user_input)
            window['-LOG-'].update(f"あなた：{user_input}\nオボエタヨ：{response}\n", append=True)
            window['-INPUT-'].update('')

    # 気分表示を更新
    window['-MOOD-'].update(f"【気分：{ai.mood}】")

window.close()
