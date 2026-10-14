# Guardian — notes for Claude Code

AI scam shield for families. Built for Daytona HackSprint NYC (Fri Oct 16, 2026). Demo persona: Rosa (protected, Spanish), Daniel (guardian, English).

## Layout
- `backend/` FastAPI. `app/pipeline.py` is the case engine; `app/rules.py` decides verdicts (LLM only extracts signals).
- `web/` Next.js 15 App Router. `src/lib/guardian.ts` holds the one SSE connection (`useGuardian`) every screen reads.
- Event names in `backend/README.md` are the contract between the two. Add events there first.

## Commands (Windows-friendly: use `python run.py`, there is no `make` on Windows)
- Backend mock: `cd backend && python run.py mock`, then `python run.py demo link|family|money`, `python run.py watch`
- Backend with real keys from `.env`: `python run.py dev`
- Tests: `python run.py test` and `python run.py eval`
- Sponsor smoke tests: `python run.py check elevenlabs|daytona|anchor|surreal|phoenix|bedrock`
- Web: `cd web && npm run dev` (needs `NEXT_PUBLIC_API_URL`, default http://localhost:8000)

## Rules that must not break
- Guardian never approves money; only Daniel's press-and-hold (`POST /cases/{id}/key`) can. No timeout auto-approves.
- Nothing Guardian says may ask for codes, passwords, cards or payments (`live_evals.asks_for_secrets`, tests enforce).
- Every reason shown cites a rule that fired (`grounded` eval).
- Text is scrubbed before any LLM call or trace.
- Only `backend/mock_sites/keystone` is ever detonated on stage.
- Each sponsor has a mock twin; an unset key must never crash a case.

## Design
Fonts Young Serif (headlines) + Figtree. Colors: bg #EEF1F6, ink #161B33, accent #2E46E5, danger #D7322A, gold #B8862B.
Hero designs (Callback, Keys, Jar, Rosa call, Daniel key, Rosa help) live in the Guardian UI canvas artifact.
