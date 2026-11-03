import json

import pytest

from stylewise_fit import nisha
from stylewise_fit.nisha import NishaRequest, chat, run_tool

CTX = {"body": {"height_cm": 168, "chest_cm": 90, "waist_cm": 74, "hip_cm": 96}, "garment_size": "M"}


@pytest.fixture
def offline(monkeypatch):
    for k in ("MODEL_API_KEY", "META_API_KEY", "MUSE_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(nisha, "_env", lambda name: None)  # ignore a developer's .env


@pytest.fixture
def online(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test")
    monkeypatch.setenv("MUSE_MODEL", "muse-test")


def ask(text, ctx=CTX, share=False):
    return NishaRequest.model_validate({"messages": [{"role": "user", "content": text}], "context": ctx,
                                        "share_measurements": share})


def test_garment_cm_come_from_fixture_not_model():
    r = run_tool({"garment_size": "M", "height_cm": 168, "chest_cm": 90})
    assert r.regions["chest"].garment_cm == 98
    assert r.provenance.garment_source.startswith("SYNTHETIC")


def test_unknown_garment_size_rejected():
    with pytest.raises(ValueError):
        run_tool({"garment_size": "XXL", "height_cm": 168})


def test_offline_answers_from_engine(offline):
    r = chat(ask("Will the M fit?"))
    assert r.source == "engine-template"
    assert r.report.regions["chest"].ease_cm == 8
    assert "beta" in r.reply.lower()


def test_offline_without_context_asks_for_measurements(offline):
    r = chat(ask("hi", ctx={}))
    assert r.report is None and "measurements" in r.reply


def test_muse_tool_loop(online, monkeypatch):
    seen = []

    def fake_chat(messages):
        seen.append(messages)
        if len(seen) == 1:
            args = {"garment_size": "S", "height_cm": 168, "chest_cm": 90, "waist_cm": 74}
            return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "evaluate_fit", "arguments": json.dumps(args)}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "Beta, the S is tight at the chest."}}]}

    monkeypatch.setattr(nisha, "_chat", fake_chat)
    r = chat(ask("What about the S?", share=True))  # the user agreed to share their measurements
    assert r.source == "muse" and r.report.regions["chest"].verdict == "tight"
    tool_msg = seen[1][-1]
    assert tool_msg["role"] == "tool" and "advice_facts" in json.loads(tool_msg["content"])
    assert "168" in seen[0][0]["content"]  # form context reaches the system prompt


def test_bad_tool_args_go_back_to_model(online, monkeypatch):
    calls = iter([
        {"choices": [{"message": {"role": "assistant", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "evaluate_fit", "arguments": "{}"}}]}}]},
        {"choices": [{"message": {"role": "assistant", "content": "Beta, which size?"}}]},
    ])
    monkeypatch.setattr(nisha, "_chat", lambda m: next(calls))
    r = chat(ask("fit?"))
    assert r.reply == "Beta, which size?" and r.report is None


def test_offline_with_catalogue_garment(offline):
    r = chat(ask("Will the kurta fit?", ctx={**CTX, "garment_id": "green-kurta"}))
    assert r.report.garment_mesh_ref is None and r.report.regions["chest"].garment_cm == 99


def test_personal_details_are_scrubbed_but_measurements_kept():
    from stylewise_fit.privacy import scrub

    text = ("Hi, my name is Riddhima Jain, email riddhima@example.com, call +65 9123 4567. "
            "I live at 50 Nanyang Avenue. I'm 165 cm with a 92 cm bust.")
    out = scrub(text)
    for secret in ("Riddhima", "example.com", "9123", "Nanyang"):
        assert secret not in out
    assert "165 cm" in out and "92 cm" in out


def test_measurements_stay_on_the_server_without_consent(monkeypatch):
    from stylewise_fit import nisha

    sent = []

    def fake_chat(messages):
        sent.append(json.dumps(messages))
        if len(sent) == 1:  # first round: Muse asks for the fit check with garment arguments only
            return {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": "t1", "type": "function", "function": {
                    "name": "evaluate_fit", "arguments": json.dumps({"garment_id": "zesica-black-midi-dress",
                                                                     "garment_size": "M"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "Beta, M works."}}]}

    monkeypatch.setattr(nisha, "_chat", fake_chat)
    monkeypatch.setattr(nisha, "muse_configured", lambda: True)
    req = nisha.NishaRequest(
        messages=[nisha.ChatTurn(role="user", content="Does M fit? I'm Asha, asha@mail.com")],
        context=nisha.FitContext(body={"height_cm": 163, "chest_cm": 91.3, "waist_cm": 74.7, "hip_cm": 99.1},
                                 garment_id="zesica-black-midi-dress", garment_size="M"))
    reply = nisha.chat(req)
    everything = " ".join(sent)
    assert reply.report is not None  # the fit ran locally with the real body
    for private in ("91.3", "74.7", "99.1", "163", "asha@mail.com"):
        assert private not in everything
