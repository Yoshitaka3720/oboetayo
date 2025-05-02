# ai.py
# core/ai.py

import random
import time
from queue import Queue, Empty
from core.response_patterns import SELF_TALK, SUBJECTIVE

class AI:
    """
    コアロジック：UI（GUI/Web）に依存しない AI エンジン部分。
    pull_events() により外部から定期的に呼び出され、
    ユーザー入力や自発発話イベントをイベントキューに積む。
    """
    def __init__(self, *, chattiness: float = 0.5, idle_threshold: float = 5.0):
        # セルフトーク用パラメータ
        self.current_task    = None        # 取り組み中のタスク名
        self.mood_val        = 0.0         # 気分を数値で表現（–1.0～1.0）
        self.chattiness     = chattiness   # 独り言発話確率（0.0～1.0）
        self.idle_threshold  = idle_threshold  # 何秒無操作でセルフトーク発生可と見るか
        self._last_activity  = time.time()    # 最終活動時刻
        # イベントキュー（UI 側で get して表示する）
        self.event_queue     = Queue()

        # --- 既存の初期化処理 ---
        # ここにメモリマネージャなど他のコアコンポーネント初期化を追加
        # self.memory_manager = MemoryManager()
        # …

    def _pick_self_talk(self) -> str:
        """
        SELF_TALK のテンプレート辞書から、文脈に応じた
        directive／affect／thinking のいずれかを選び、
        フォーマットして返す。
        """
        if self.current_task:
            tpl = random.choice(SELF_TALK["directive"])
            return tpl.format(task=self.current_task)
        elif abs(self.mood_val) > 0.5:
            return random.choice(SELF_TALK["affect"])
        else:
            return random.choice(SELF_TALK["thinking"])

    def _should_fire(self) -> bool:
        """
        無操作時間が閾値 idle_threshold を超えたかどうかをチェック。
        """
        return (time.time() - self._last_activity) >= self.idle_threshold

    def _spontaneous_loop(self):
        """
        一定時間操作がない場合に、chattiness 確率で
        SELF_TALK 由来のセルフトークのみを発話する。
        """
        if self._should_fire() and random.random() < self.chattiness:
            text = self._pick_self_talk()
            self._emit(text)
            self._last_activity = time.time()
            
    def pull_events(self, user_input: str = None):
        """
        メインループ／UI から定期呼び出しされるメソッド。
        引数 user_input があればその学習＆応答を行い、
        無ければ自発発話タイミングをチェックする。
        """
        # 1) ユーザー入力があれば即応答
        if user_input is not None:
            response = self.learn(user_input)
            self._emit(("response", response))
            self._last_activity = time.time()

        # 2) 自発発話（idle_threshold 経過後に発火）
        self._spontaneous_loop()

        # 3) キュー内のイベントをすべて返す
        events = []
        while True:
            try:
                events.append(self.event_queue.get_nowait())
            except Empty:
                break
        return events

    def _emit(self, event):
        """
        イベントキューに積む。event は ("type", message) のタプル。
        UI 側は pull_events() の戻り値を見て表示を行う。
        """
        self.event_queue.put(event)

    def learn(self, text: str) -> str:
        """
        ユーザーからの入力に基づいて学習／応答を生成し返す。
        """
        # --- 既存の学習・応答ロジック ---
        # resp = …
        resp = "応答例：" + text  # 仮応答
        # 応答後は最終活動時刻を更新
        self._last_activity = time.time()
        return resp
