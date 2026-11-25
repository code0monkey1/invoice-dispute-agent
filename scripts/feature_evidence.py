"""Select and run checked-in merge evidence, then publish only successful results."""

import argparse
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path(__file__).with_suffix(".json")
CHANNEL = "C0CJJPTLWM9"


def select(event):
    body = event["pull_request"].get("body") or ""
    declarations = []
    commented = False
    for line in body.splitlines():
        if "<!--" in line:
            commented = True
        if not commented and line.startswith("Evidence:"):
            declarations.append(line.removeprefix("Evidence:").strip())
        if "-->" in line:
            commented = False
    if len(declarations) != 1:
        raise ValueError("Declare exactly one Evidence: line in the pull request body.")
    if declarations[0] == "ci-only":
        return {"mode": "ci-only"}

    match = re.fullmatch(r"(browser-video|test-summary) ([a-z0-9-]+)", declarations[0])
    if not match:
        raise ValueError("Use browser-video <scenario>, test-summary <scenario>, or ci-only.")
    mode, scenario = match.groups()
    selection = json.loads(CATALOG.read_text(encoding="utf-8")).get(scenario)
    if not selection or selection["mode"] != mode:
        raise ValueError(f"Unknown {mode} scenario '{scenario}'. Check scripts/feature_evidence.json.")
    return selection


def run(selection, record):
    if selection["mode"] == "test-summary":
        subprocess.run([sys.executable, "-m", "pytest", "-q", selection["target"]], cwd=ROOT, check=True)
    elif selection["mode"] == "browser-video":
        env = {**os.environ, "VITE_API_URL": "", "RECORD_FEATURE_EVIDENCE": "1" if record else "0"}
        frontend = ROOT / "frontend"
        subprocess.run(["npm", "run", "build"], cwd=frontend, env=env, check=True)
        subprocess.run(["npm", "exec", "--", "playwright", "test", selection["target"]],
                       cwd=frontend, env=env, check=True)


def collect(selection, test_results, out):
    mode = selection["mode"]
    out.mkdir(parents=True, exist_ok=True)
    if mode == "browser-video":
        clips = sorted(test_results.glob("*/clips/*.webm"))
        if not clips or any(clip.stat().st_size == 0 for clip in clips):
            raise ValueError("The passing browser test did not produce a complete recording.")
        inputs = [argument for clip in clips for argument in ("-i", str(clip))]
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", *inputs,
             "-filter_complex", f"concat=n={len(clips)}:v=1:a=0", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "demo.mp4")],
            check=True,
        )
    elif mode != "test-summary":
        raise ValueError("Only passing video or summary scenarios can produce evidence.")
    (out / "result.json").write_text(
        json.dumps({"mode": mode, "description": selection["description"]}), encoding="utf-8",
    )


def slack_api(token, method, data):
    is_upload_request = method == "files.getUploadURLExternal"
    body = urlencode(data).encode() if is_upload_request else json.dumps(data).encode()
    request = Request(
        f"https://slack.com/api/{method}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded" if is_upload_request else "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise ValueError(f"Slack {method} failed: {result.get('error', 'unknown_error')}")
    return result


def upload_bytes(url, body):
    target = urlsplit(url)
    if target.scheme != "https" or target.netloc != "files.slack.com":
        raise ValueError("Slack did not return a recognized file upload endpoint.")
    request = Request(url, data=body, headers={"Content-Type": "application/octet-stream"})
    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise ValueError(f"Slack file transfer failed with HTTP {response.status}.")


def publish(artifact, token, pr_url, run_url):
    if not token:
        raise ValueError("Configure the GitHub Actions SLACK_BOT_TOKEN secret before publishing.")
    result = json.loads((artifact / "result.json").read_text(encoding="utf-8"))
    text = f"{escape(result['description'], quote=False)}\n<{pr_url}|Pull request> · <{run_url}|Passing CI run>"
    if result["mode"] == "test-summary":
        sent = slack_api(token, "chat.postMessage", {"channel": CHANNEL, "text": text, "unfurl_links": False})
        print(f"Slack accepted the summary in {CHANNEL} (message {sent.get('ts', 'accepted')}).")
    elif result["mode"] == "browser-video":
        video = (artifact / "demo.mp4").read_bytes()
        if not video:
            raise ValueError("The passing recording is empty.")
        upload = slack_api(token, "files.getUploadURLExternal", {"filename": "invoicechaser-demo.mp4", "length": len(video)})
        upload_bytes(upload["upload_url"], video)
        sent = slack_api(token, "files.completeUploadExternal", {
            "files": [{"id": upload["file_id"], "title": "InvoiceChaser feature test"}],
            "channel_id": CHANNEL,
            "initial_comment": text,
        })
        print(f"Slack accepted the video in {CHANNEL} (file {upload['file_id']}).")
        for file in sent.get("files", []):
            if file.get("permalink"):
                print(file["permalink"])
    else:
        raise ValueError("This evidence mode cannot publish to Slack.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("select", "run", "collect", "publish"))
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    try:
        if args.operation == "publish":
            publish(Path(os.environ["EVIDENCE_DIR"]), os.getenv("SLACK_BOT_TOKEN"),
                    os.environ["PR_URL"], os.environ["RUN_URL"])
            return
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        selection = select(event)
        if args.operation == "select":
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"mode={selection['mode']}\n")
        elif args.operation == "run":
            run(selection, args.record)
        else:
            collect(selection, ROOT / "frontend" / "test-results", Path(os.environ["EVIDENCE_DIR"]))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Feature evidence {args.operation} failed: {error}\n")


if __name__ == "__main__":
    main()
