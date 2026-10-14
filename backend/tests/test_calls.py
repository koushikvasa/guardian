import os, sys
os.environ["GUARDIAN_MOCK"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import calls


def test_captions_drop_voice_delivery_tags_but_keep_words():
    assert calls.caption("[slow] Thank you, Rosa. [warm] You are safe.") == "Thank you, Rosa. You are safe."
    assert "[" not in calls.caption("[happy] That is perfect, Rosa. [warm] Goodbye.")
    assert calls.caption(None) == ""


def test_result_from_done_conversation_reads_data_collection():
    conv = {"status": "done", "transcript": [{"role": "agent", "message": "[slow] Hi"}, {"role": "user", "message": "I will send it to you first"}],
            "analysis": {"data_collection_results": {"teach_back_ok": {"value": True, "rationale": "..."}}}}
    r = calls._result_from_conversation(conv, connected=True)
    assert r["status"] == "completed" and r["data"] == {"teach_back_ok": True} and r["transcript"][0]["message"] == "Hi"


def test_no_user_speech_counts_as_no_answer():
    conv = {"status": "done", "transcript": [{"role": "agent", "message": "Hi"}], "analysis": {}}
    assert calls._result_from_conversation(conv, connected=True)["status"] == "no_answer"
