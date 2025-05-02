# tests/test_self_talk_type.py

import pytest
from core.ai import AI

def test_self_talk_directive():
    ai = AI()
    ai.current_task = "お茶をいれる"
    # current_task があるときは directive テンプレから出力される
    text = ai._pick_self_talk()
    assert "お茶" in text

def test_self_talk_affect():
    ai = AI()
    ai.current_task = None
    ai.mood_val = 0.7
    # mood_val の絶対値が 0.5 を超えると affect テンプレから出力される
    text = ai._pick_self_talk()
    assert any(keyword in text for keyword in ["やった", "しまった", "嬉しい"])

def test_self_talk_thinking():
    ai = AI()
    ai.current_task = None
    ai.mood_val = 0.0
    # 上記以外のときは thinking テンプレから出力される
    text = ai._pick_self_talk()
    assert any(keyword in text for keyword in ["どうしよう", "うーん"])