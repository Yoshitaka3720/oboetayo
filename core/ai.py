# ai.py

import random
import time
import threading
import asyncio
from datetime import datetime, timedelta

from core.memory import MemoryManager
from core.time_manager import TimeManager
from core.speech_patterns import is_greeting, get_greeting_response, get_greeting_type
from core.utils import normalize_text

class AI:
    def __init__(self):
        # —— 感情ステート ——
        self.moods = ["happy", "neutral", "tired"]
        self.mood = random.choice(self.moods)
        self.next_mood_shift = datetime.now() + timedelta(hours=1)

        # —— 永続層 ——
        self.memory = MemoryManager("memory.db")
        self.time = TimeManager("last_seen.txt")

        # —— 自発発話パラメータ ——
        self.fire_prob      = 0.4
        self.cooldown       = 180
        self.min_strength   = 0.9
        self.idle_threshold = 120
        self._last_spont_ts  = 0
        self._last_spont_msg = None
        self.last_user_ts    = time.time()
        self._spont_started  = False

        # —— ユーザー連呼検知用 ——
        self.last_user_message = None
        self.repeat_count = 0

    def think(self):
        """記憶の減衰＋1時間ごとに気分を更新"""
        self.memory.decay()
        now = datetime.now()
        if now >= self.next_mood_shift:
            self.mood = random.choice(self.moods)
            self.next_mood_shift = now + timedelta(hours=1)

    def learn(self, message: str) -> str:
        """
        ユーザー入力 handling:
         - 空入力反応
         - '覚えてる' リコール＋迷い表現
         - 同じ単語連呼リアクション
         - 挨拶判定
         - 一般返答
        """
        # タイムスタンプ更新
        self.last_user_ts = time.time()
        raw = message.strip()
        norm = normalize_text(raw)

        # —— 空入力 ——
        if not raw:
            return random.choice([
                "何か話してよ〜",
                "ねえってば…",
                "……無視しないでよ（しょんぼり）"
            ])

        # —— '覚えてる' リコール ——
        if "覚えてる" in norm:
            key = norm.replace("覚えてる", "")
            # ただの「覚えてる？」だけ
            if not key:
                mems = self.memory.get_all()
                if mems:
                    return f"うん、『{mems[0][0]}』って言ってたよね！"
                else:
                    return "うーん、あんまり覚えてないかも…"
            # 部分一致＋長さ差スコアリング
            best_score = float("inf")
            best_match = None
            best_strength = 0.0
            for mem, strength in self.memory.get_all():
                if key in normalize_text(mem):
                    score = abs(len(mem) - len(key))
                    if score < best_score:
                        best_score = score
                        best_match = mem
                        best_strength = strength
            if best_match:
                if best_strength >= 0.6:
                    return f"うん、『{best_match}』って言ってたよね！"
                elif best_strength >= 0.4:
                    return random.choice([
                        f"たしか『{best_match}』だった気がするよ",
                        f"うーん、『{best_match}』って言ってたような…",
                        f"覚えてるけどちょっと自信ないな…『{best_match}』かな？"
                    ])
                elif best_strength >= 0.05:
                    return random.choice([
                        f"うろ覚えだけど、『{best_match}』だったかも…",
                        f"あんまり覚えてないけど『{best_match}』って言ってたかも",
                        f"記憶が曖昧だけど…たぶん『{best_match}』？"
                    ])
                else:
                    return "うーん、全然思い出せないかも…"
            else:
                return f"ごめん、『{key}』については覚えてないかも…"

        # —— 同じ入力連呼リアクション ——
        if raw == self.last_user_message:
            self.repeat_count += 1
        else:
            self.repeat_count = 0
        self.last_user_message = raw
        if self.repeat_count >= 2:
            self.memory.add(raw)
            return random.choice([
                f"また『{raw}』！？もう聞いたよ〜（笑）",
                f"さっきも『{raw}』って言ったじゃん！（苦笑）",
                f"そんなに『{raw}』が大事なの？（笑）"
            ])

        # —— 記憶登録 ——
        self.memory.add(raw)

        # —— 挨拶判定 ——
        if is_greeting(norm):
            gtype = get_greeting_type(norm)
            return get_greeting_response(gtype, False, self.mood)

        # —— 一般返答 ——
        msg, strength = self.memory.get_all()[0]
        suffix = {"happy":"！😄","neutral":"。","tired":"…😪"}[self.mood]
        if strength > 0.8:
            return random.choice([
                f"うん、{msg}って言ってたよね！",
                f"{msg}…よく覚えてる！",
                f"それそれ、{msg}！"
            ]) + suffix
        elif strength > 0.4:
            return random.choice([
                f"たしか『{msg}』だった気がする…",
                f"{msg}って話してたかも…"
            ]) + suffix
        else:
            return random.choice([
                "うーん、思い出せないな…",
                "なんか言ってた気がするけど忘れた…"
            ]) + suffix

    async def _spontaneous_loop(self, callback):
        """自発発話ループ"""
        try:
            while True:
                await asyncio.sleep(30)
                self.think()
                if time.time() - self.last_user_ts < self.idle_threshold:
                    continue
                mems = self.memory.get_all()
                if not mems:
                    continue
                msg, strength = mems[0]
                if strength < self.min_strength:
                    continue
                if random.random() > self.fire_prob:
                    continue
                now = time.time()
                if now - self._last_spont_ts < self.cooldown:
                    continue
                if msg == self._last_spont_msg:
                    continue
                self._last_spont_ts  = now
                self._last_spont_msg = msg
                callback(f"そういえば、『{msg}』って言ってたよね？")
        except asyncio.CancelledError:
            pass

    def start_spontaneous(self, callback):
        """非同期自発発話開始"""
        if self._spont_started:
            return
        self._spont_started = True
        threading.Thread(
            target=lambda: asyncio.run(self._spontaneous_loop(callback)),
            daemon=True
        ).start()
