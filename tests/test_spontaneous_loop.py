import time
import pytest
from core.ai import AI
from core.response_patterns import SELF_TALK 

class DummyAI(AI):
    """_emit の出力をリストにため込むテスト用サブクラス"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.emitted = []

    def _emit(self, message):
        # イベントキューではなく直接 emitted リストに保存
        self.emitted.append(message)

    def _reset_activity(self, offset_seconds: float):
        # 最終活動時刻を現在から offset_seconds 遡らせる
        self._last_activity = time.time() - offset_seconds

def test_spontaneous_loop_fires_when_idle_and_chattiness_1():
    ai = DummyAI(chattiness=1.0, idle_threshold=0.1)
    # 直前の activity を十分に過去に設定
    ai._reset_activity(offset_seconds=1.0)
    # 呼び出し → 必ず発話
    ai._spontaneous_loop()
    assert len(ai.emitted) == 1
    msg = ai.emitted[0]
    # SELF_TALK のいずれかのテンプレから来ているか
    assert any(msg in tpl or tpl in msg for tpl in sum(SELF_TALK.values(), []))

def test_spontaneous_loop_does_not_fire_if_not_idle():
    ai = DummyAI(chattiness=1.0, idle_threshold=10.0)
    # まだ idle_threshold 秒経っていない
    ai._reset_activity(offset_seconds=0.1)
    ai._spontaneous_loop()
    assert ai.emitted == []

def test_spontaneous_loop_honors_chattiness_probability(monkeypatch):
    # chattiness=0 → 絶対発話しない
    ai_zero = DummyAI(chattiness=0.0, idle_threshold=0.0)
    ai_zero._reset_activity(offset_seconds=1.0)
    ai_zero._spontaneous_loop()
    assert ai_zero.emitted == []

    # chattiness=0.5 をシード固定で試す
    ai_half = DummyAI(chattiness=0.5, idle_threshold=0.0)
    ai_half._reset_activity(offset_seconds=1.0)
    # random.random() を常に 0.4 に固定 → 発話される
    monkeypatch.setattr("random.random", lambda: 0.4)
    ai_half._spontaneous_loop()
    assert len(ai_half.emitted) == 1

    # random.random() を常に 0.6 に固定 → 発話されない
    ai_half.emitted.clear()
    monkeypatch.setattr("random.random", lambda: 0.6)
    ai_half._reset_activity(offset_seconds=1.0)
    ai_half._spontaneous_loop()
    assert ai_half.emitted == []

