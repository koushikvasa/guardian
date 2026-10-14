PY ?= python3
PORT ?= 8000

install:
	$(PY) -m pip install -r requirements.txt

dev:
	$(PY) -m uvicorn app.main:app --reload --port $(PORT)

mock:
	GUARDIAN_MOCK=1 MOCK_KEY_DECISION=decline VERIFY_RETRY_AFTER_S=5 $(PY) -m uvicorn app.main:app --port $(PORT)

demo-link:
	curl -s -X POST localhost:$(PORT)/demo/link; echo
demo-family:
	curl -s -X POST localhost:$(PORT)/demo/family; echo
demo-money:
	curl -s -X POST localhost:$(PORT)/demo/money; echo
watch:
	curl -sN localhost:$(PORT)/events

decline:
	curl -s -X POST localhost:$(PORT)/cases/$(CASE)/key -H 'content-type: application/json' -d '{"decision":"decline"}'; echo

eval:
	$(PY) evals/run_eval.py

test:
	$(PY) -m pytest -q tests

phoenix:
	phoenix serve
surreal:
	surreal start --bind 0.0.0.0:8001 --user root --pass root memory
tunnel:
	cloudflared tunnel --url localhost:$(PORT)
