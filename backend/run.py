"""Cross-platform task runner (Windows has no `make`).

  python run.py mock            all sponsors mocked; money waits for Daniel's button
  python run.py dev             real keys from .env (unset keys stay mocked)
  python run.py demo link       fire a demo beat: link | family | money
  python run.py decline A-2041  Daniel's "Don't send it" from the terminal
  python run.py watch           print the live event stream
  python run.py test            unit tests
  python run.py eval            offline eval -> data/scoreboard.json
  python run.py check <name>    smoke test: elevenlabs | daytona | anchor | surreal | phoenix | bedrock
"""
import json
import os
import subprocess
import sys
import urllib.request

PORT = os.environ.get("PORT", "8787")
BASE = f"http://localhost:{PORT}"
PY = sys.executable


def serve(extra_env: dict, reload: bool):
    env = {**os.environ, **extra_env}
    cmd = [PY, "-m", "uvicorn", "app.main:app", "--port", PORT]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd, env=env)


def post(path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(BASE + path, data=data, method="POST", headers={"content-type": "application/json"})
    print(urllib.request.urlopen(req).read().decode())


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "mock":
        serve({"GUARDIAN_MOCK": "1", "MOCK_KEY_DECISION": "", "VERIFY_RETRY_AFTER_S": "5"}, reload=False)
    elif cmd == "dev":
        serve({}, reload=True)
    elif cmd == "demo":
        post(f"/demo/{rest[0] if rest else 'link'}?lang={rest[1] if len(rest) > 1 else 'es'}")
    elif cmd == "decline":
        post(f"/cases/{rest[0]}/key", {"decision": "decline"})
    elif cmd == "watch":
        with urllib.request.urlopen(BASE + "/events") as r:
            for line in r:
                line = line.decode().strip()
                if line.startswith("data: "):
                    e = json.loads(line[6:])
                    if e["kind"] != "ping":
                        print(f"{e['kind']:<28} {e.get('case') or '':<8} {json.dumps({k: v for k, v in e.items() if k not in ('t', 'kind', 'case')}, ensure_ascii=False)[:140]}")
    elif cmd == "test":
        sys.exit(subprocess.call([PY, "-m", "pytest", "-q", "tests"]))
    elif cmd == "eval":
        sys.exit(subprocess.call([PY, "evals/run_eval.py"]))
    elif cmd == "check":
        name = {"surreal": "surreal", "surrealdb": "surreal"}.get(rest[0], rest[0])
        sys.exit(subprocess.call([PY, f"scripts/check_{name}.py", *rest[1:]]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
