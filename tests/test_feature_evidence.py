import json

import pytest

from scripts import feature_evidence as evidence


@pytest.mark.parametrize(("declaration", "mode"), [
    ("browser-video invoice-number-ownership", "browser-video"),
    ("test-summary invoice-owner-api", "test-summary"),
    ("ci-only", "ci-only"),
])
def test_selects_one_explicit_mode(declaration, mode):
    # A backend-only PR can still explicitly declare a browser scenario.
    selected = evidence.select({"pull_request": {"body": f"Evidence: {declaration}", "changed_files": 1}})
    assert selected["mode"] == mode


@pytest.mark.parametrize("body", [
    None, "", "Evidence: browser-video", "Evidence: browser-video unknown",
    "Evidence: test-summary invoice-number-ownership", "Evidence: ci-only extra",
    "Evidence: ci-only\nEvidence: browser-video invoice-number-ownership",
    "Evidence: browser-video invoice-number-ownership; echo nope",
])
def test_rejects_invalid_selection(body):
    with pytest.raises(ValueError):
        evidence.select({"pull_request": {"body": body}})


def test_missing_video_cannot_produce_passing_evidence(tmp_path):
    with pytest.raises(ValueError, match="recording"):
        evidence.collect({"mode": "browser-video", "description": "test"}, tmp_path, tmp_path / "out")
    assert not (tmp_path / "out" / "result.json").exists()


def test_summary_collection_creates_result(tmp_path):
    out = tmp_path / "out"
    evidence.collect({"mode": "test-summary", "description": "test"}, tmp_path, out)
    assert json.loads((out / "result.json").read_text()) == {"mode": "test-summary", "description": "test"}


def test_publish_video_uses_slack_upload_and_channel(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text(json.dumps({"mode": "browser-video", "description": "Owners isolated"}))
    (tmp_path / "demo.mp4").write_bytes(b"video")
    sent = []

    def api(token, method, data):
        sent.append((method, data))
        if method == "files.getUploadURLExternal":
            return {"upload_url": "https://files.slack.com/upload/example", "file_id": "F1"}
        return {}

    monkeypatch.setattr(evidence, "slack_api", api)
    monkeypatch.setattr(evidence, "upload_bytes", lambda url, body: sent.append((url, body)))
    evidence.publish(tmp_path, "token", "https://github.com/example/repo/pull/2", "https://github.com/example/repo/actions/runs/3")
    assert [call[0] for call in sent] == [
        "files.getUploadURLExternal", "https://files.slack.com/upload/example", "files.completeUploadExternal",
    ]
    assert sent[1][1] == b"video"
    payload = sent[2][1]
    assert payload["channel_id"] == "C0CJJPTLWM9"
    assert "Owners isolated" in payload["initial_comment"]
    assert "/pull/2" in payload["initial_comment"]
    assert "/actions/runs/3" in payload["initial_comment"]


def test_publish_summary_and_surface_slack_failure(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text(json.dumps({"mode": "test-summary", "description": "Ownership checked"}))

    def api(token, method, data):
        assert method == "chat.postMessage"
        assert data["channel"] == "C0CJJPTLWM9"
        assert "Ownership checked" in data["text"]
        raise ValueError("Slack rejected the request")

    monkeypatch.setattr(evidence, "slack_api", api)
    with pytest.raises(ValueError, match="Slack rejected"):
        evidence.publish(tmp_path, "token", "https://github.com/example/repo/pull/2", "https://github.com/example/repo/actions/runs/3")


@pytest.mark.parametrize("mode", [None, "ci-only"])
def test_publish_requires_passing_evidence(tmp_path, mode):
    if mode:
        (tmp_path / "result.json").write_text(json.dumps({"mode": mode, "description": "test"}))
    with pytest.raises((OSError, ValueError)):
        evidence.publish(tmp_path, "token", "", "")
