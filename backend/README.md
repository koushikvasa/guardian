# Guardian: AI scam shield for families

Rosa forwards a suspicious text to Guardian's number. Guardian:
- opens any link in a sealed sandbox (**Hero 3**)
- calls the real relative on their saved number when someone claims to be family (**Hero 1**)
- holds any money request until a second family member turns the key (**Hero 2**)
- calls Rosa in Spanish with the family safe phrase and a teach-back question, then offers her a voice note to warn friends

## Run it now (mock mode, no keys)

```bash
pip install fastapi "uvicorn[standard]" httpx python-multipart python-dotenv pytest
make mock            # API on :8000; every sponsor mocked
make watch           # in a 2nd terminal: live event stream
make demo-link       # Hero 3
make demo-family     # Hero 1
make demo-money      # Hero 2 (auto-declines in `make mock`; with `make dev`, run: make decline CASE=A-2043)
make test && make eval
```

## Go live, one sponsor at a time

`cp .env.example .env`. Fill in one block, restart, and check `GET /health`, which shows each sponsor as live or mock.
Run the smoke tests in risk order:

| # | Script | Proves |
|---|---|---|
| 1 | `python scripts/check_elevenlabs.py +1YOURPHONE es` | A real Spanish call reaches your phone |
| 2 | `python scripts/check_daytona.py` | Sandbox starts, reaches the network, deletes |
| 3 | `python scripts/check_anchor.py https://example.com` | Anchor session + screenshot |
| 4 | `python scripts/check_memory.py` | SurrealDB Agent Memory: typed fact in, recall with a trace id out |
| 4b | `make surreal` then `python scripts/check_surreal.py` | Trust graph + herd fingerprints (self-hosted SurrealDB) |
| 5 | `python scripts/check_arize.py` | A trace and an experiment land in Arize AX (or `make phoenix` + `check_phoenix.py` for local Phoenix) |
| 6 | `python scripts/check_bedrock.py` | Bedrock signal JSON |

ElevenLabs agent prompts are in `agents/`. Each one lists its first message, system prompt and data-collection fields.

## Map

```
app/main.py          routes: /sms (Twilio), /events (SSE), /cases, /cases/{id}/key, /demo/*, /scoreboard, /family
app/pipeline.py      the case engine + the three heroes + warning call + help note
app/rules.py         deterministic verdict; every reason cites a rule (weights 0-29 safe, 30-59 suspicious, 60+ scam)
app/signals.py       Bedrock JSON extraction (regex twin) + Textract OCR
app/detonate.py      Daytona sandbox -> app/sandbox_job.py -> Anchor browser (or quarantine: Anchor here, parse in sandbox)
app/quarantine_job.py runs inside the sandbox with no network: parses the untrusted HTML (forms, brands, frames)
app/memory.py        SurrealDB Agent Memory: trust facts + remembered verdicts, recalled with a trace (mock twin)
app/calls.py         ElevenLabs outbound calls, live captions by polling, post-call webhook
app/graph.py         SurrealDB trust graph + scam fingerprints (in-memory twin)
app/live_evals.py    grounded / no-asks / language checks on every case (Phoenix span attrs)
evals/run_eval.py    offline experiment -> data/scoreboard.json (+ Phoenix experiment)
mock_sites/keystone  the ONLY page ever detonated on stage (fictional bank, form sends nothing)
```

## Events the UI listens to (GET /events)

`case.opened` · `sms.in` · `sms.out` · `signals` · `detonation.started` · `detonation.result` · `verdict` ·
`money.locked` · `key.decision` · `call.{warning|verify|second_key}.{dialing|connected|transcript|ended}` ·
`verify.outcome` · `teachback` · `help.note.ready` · `herd.recorded` · `eval.live` · `case.closed` ·
`memory.recalled` `{hits:[{text,when,score}], trace_id, tier, prior_scam:{what,date}|null}` · `memory.remembered` `{text, entities}` ·
`help.note.ready` also carries `link` (the public `GET /help/{id}` page served by the backend)

Every event is also appended to `data/events.log.jsonl`. That file is the stage backup: replay it into the UI if the network dies.

## Safety rules the code enforces

- Guardian never approves money. Approval only comes from Daniel's press-and-hold in the app. A timeout leaves the money locked.
- Nothing Guardian says asks for codes, passwords, cards or payments. This is checked live on every case and in `tests/`.
- Text is scrubbed (cards, SSNs, emails, codes) before any LLM call or trace.
- Detonation only observes. It never types, submits or downloads, and the sandbox is deleted afterwards.
- On stage, only `mock_sites/keystone` is ever opened. Never open a live scam site.

## Still to do (owner: you)

- [ ] Before exposing the server publicly, verify the ElevenLabs webhook HMAC (TODO in `main.py`).
- [ ] Add 80 unseen Spanish rows to `evals/es_handwritten.extra.csv`. Also build `evals/hf.extra.csv` with `evals/build_set.py`. The seed set is small and matches the regexes, so its score is optimistic.
- [ ] Story Check and Live Challenge are pitch-only (not built).
