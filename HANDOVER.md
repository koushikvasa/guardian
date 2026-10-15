# Guardian: handover brief

Written for: a Claude session (or engineer) picking this up cold on demo day, Fri 16 Oct 2026, Daytona HackSprint NYC (venue: AWS, 12 W 39th St). Devpost deadline 3:30 PM; submit by 3:00.

## What Guardian is

An AI scam shield for families. A protected parent (Amma, Telugu; Jasmine, English; Rosa, Spanish) never has to do anything: texts from strangers are forwarded by her phone automatically, or she tells Guardian in her own words on WhatsApp. Guardian then:

1. **Safe link opening.** Fetches the link (Anchor cloud browser when credited, plain fetch otherwise), parses the page inside a throwaway Daytona sandbox with no network, destroys the sandbox, and scores what it found.
2. **Verify by callback.** When someone claims to be family, calls the real relative (Daniel) on the number the family saved and asks one question.
3. **Money second key.** Any money request above the family threshold is locked until Daniel presses and holds on his own phone. Guardian never approves; a spoken yes never approves; no timeout.
4. **Tech-support call.** Amma reports a "Microsoft" call in her own words; remote-access, fake-support, callback-number and gift-card signals lock the money and call Daniel.

Every scam ends with a warning call to her in her language that opens with the family's private phrase, explains two reasons, and asks her to say back what she'll do next time (teach-back). Then a help note (text + audio page) for her friends, and the verdict is remembered.

**Rules that must not break:** rules decide, not the model (every reason cites a rule id); Guardian never asks for codes, passwords, cards or payments (live eval enforces); text is scrubbed before any LLM or trace; only `backend/mock_sites/keystone` is ever detonated; every sponsor has a mock twin, an unset key never crashes a case.

## Repo layout

- `backend/` FastAPI. `app/pipeline.py` case engine; `app/rules.py` verdict; `app/signals.py` extraction (Bedrock or regex twin); `app/detonate.py` + `app/quarantine_job.py` sandbox; `app/calls.py` ElevenLabs; `app/sms.py` Twilio/WhatsApp with text budget; `app/memory.py` SurrealDB Agent Memory; `app/tracing.py` Arize spans (also emitted as `span` events); `app/main.py` routes; `app/help_page.py`, `app/key_page.py` phone-openable pages; `data/seed_family.json` family (real phones come from env); `data/memory_knowledge.jsonl` 38 scam facts; `agents/*.md` the five ElevenLabs agent specs.
- `web/` Next.js 15. `/` pitch page; `/stage` the one-screen demo (phone · desk · Daniel's phone); `/family` manager page (phrases, threshold, memory graph, memory queries, today's cases); `/phone` mirror. `src/lib/guardian.ts` is the single SSE connection every screen reads. Components: `Mark` (living logo), `Desk`, `Hero` (animated jar / ring / vault), `PhoneAmma`, `PhoneDaniel`, `TraceDrawer`, `MemoryGraph`, `ModeSwitch`, `ThemeToggle`.
- Event contract between the two: `backend/README.md`.
- `backend/.env.local` holds every secret (gitignored). `.env.example` documents each key.

## Running it (Windows)

Use `.\.venv\Scripts\python.exe`, never bare `python`. Backend port 8787. Web port 3000.

```
cd backend ; .\.venv\Scripts\python.exe run.py morning 55     # tunnel + PUBLIC_BASE_URL + Twilio SMS webhook + text budget; prints 2 URLs to paste
cd backend ; .\.venv\Scripts\python.exe run.py dev            # backend (DEMO mode by default)
cd web ; npm run dev                                          # web
```
Paste the printed URL into (a) Twilio console → Messaging → Try it out → WhatsApp → Sandbox settings → "When a message comes in" = `<url>/sms`, and (b) MacroDroid → Guardian macro → HTTP request URL = `<url>/ingest`, then turn the macro on. The tunnel URL changes every restart.

Tests: `run.py test` (37 pass), `run.py eval` (47 messages, 92% catch, 0% false alarms, also logs an Arize experiment). Smoke tests: `run.py check elevenlabs|daytona|anchor|arize|memory|bedrock`.

## Modes and safety switches

- **DEMO / LIVE** (stage top bar, or `POST /mode`): DEMO runs every beat with sponsors mocked for that case (no texts, calls, sandboxes, memory writes). LIVE makes beats real. Going live takes two clicks within 3 s. Backend starts in DEMO (`DEMO_LIVE=0`). Real inbound texts are always live.
- **Text budget**: `TEXT_BUDGET` caps real WhatsApp texts (sandbox quota, ~67 left on 15 Oct evening); `TEXT_ESSENTIAL_ONLY=1` sends only scam alert, key link, help note, suspicious notice, approval. Screens show every text regardless. Counter in `data/texts_sent.json`, shown in `/health`.
- **Memory recall** is capped at 8 s so it never delays a call.

## Phones and people

One phone plays everyone: `FAMILY_PHONE_*` and `FAMILY_WHATSAPP_*` in `.env.local` all point at Koushik's phone (calls +1 571 420 2558, WhatsApp +91 72072 06510). Guardian's Twilio number is +1 571 605 6658 (US SMS *out* is blocked by 10DLC, hence WhatsApp). Phrases: Jasmine "Buckie the dog", Amma "Kanna", Rosa "flan de la abuela". Daniel is the guardian.

## Sponsor status (end of 15 Oct)

| Sponsor | Status | Notes |
|---|---|---|
| ElevenLabs + Twilio | live, proven on real calls | 5 agents (warning en/es/te, verify, second key), v4 Turbo, 120 s cap; captions arrive when a call ends |
| Arize AX | live | traces via gRPC, experiment per eval run, 3 live checks per case; trace drawer (T) on the stage |
| Daytona | live, quarantine mode | org is Tier 1/2 (no sandbox egress); snapshot `guardian-detonator`; `DETONATE_MODE=daytona` only if Tier 3 is granted |
| SurrealDB Agent Memory | live | family scope + shared `knowledge/scams` scope (38 facts); graph on `/family`; `run.py seed-memory --force` reloads |
| Anchor | key valid, no credit (402) | browser-less fallback runs; once credited nothing to configure, `run.py check anchor <url>` |
| AWS Bedrock / Textract | mocked | needs the venue lab account: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `BEDROCK_MODEL_ID`, `USE_TEXTRACT=1`, then `run.py check bedrock` |

## Demo day plan

1. Morning command, paste the two URLs, start backend and web, play 1–4 in DEMO, check `GET /health` shows mode `demo` and the text counter.
2. Anchor table first (coupon `ANCHOR_HACKSPRINT_10_16_26`), then AWS lab account, then optional Daytona Tier 3 ask on Slack.
3. Record the demo video (under 2 min) from `/stage` in DEMO, then one LIVE rehearsal of the three beats (about 8 texts).
4. Devpost: project link is the home page; description must list every sponsor and how it's used (the home page's sponsor section is that text).

## Open items (not done)

- Devpost description text and the video shot list (write first).
- Approve branch never rehearsed live; tech-support beat only run in DEMO.
- Inbound "call Guardian" line and WhatsApp voice notes: pitched as next, not built.
- Webhook HMAC check on `/webhooks/elevenlabs` before exposing beyond the tunnel.
- Two eval misses (Spanish Chase charge text, Netflix billing link) score safe.
- Spanish warning call was never heard by a Spanish speaker.

## Gotchas learned the hard way

- This shell had `GUARDIAN_MOCK=1` in its environment once; if `/health` shows `mock_forced: true`, start the backend with `GUARDIAN_MOCK=0` explicitly.
- A size container (`container-type: size`) on an ancestor freezes CSS animations inside SVGs in Chromium. The hero cell uses a ResizeObserver instead.
- Carriers split long SMS into several notifications; `/ingest` merges fragments from one sender within `INGEST_MERGE_S` (4 s).
- ElevenLabs releases the transcript only after the call ends; "connected" comes from the status field. v4 delivery tags like `[slow]` are stripped before captions.
- Phones in the stage are `overflow: clip` so a tap can't scroll their contents out of frame.
- MacroDroid's SMS trigger does not fire on the Play Store build; use the Notification trigger on the Messages app with `[not_title]` / `[not_text]`.
- The WhatsApp sandbox only delivers to numbers that joined it, and WhatsApp may live on a different number than calls (`FAMILY_WHATSAPP_*`).
