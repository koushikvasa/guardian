# Guardian

**An AI scam shield for families.** Rosa's phone sends Guardian any message with a link. Guardian opens the link in a sealed sandbox, calls the real relative before anyone sends money, and calls Rosa in Spanish to explain it.

| Hero | What happens | Sponsors |
|---|---|---|
| Safe link opening | The link is opened in a throwaway Daytona sandbox driving an Anchor cloud browser; the evidence is screenshotted, and the sandbox is destroyed | Daytona, Anchor |
| Verify-by-callback | "Mamá, soy Daniel": Guardian calls the *real* Daniel on his saved number | ElevenLabs, SurrealDB |
| Money Second Key | $2,000 wire request: money waits until Daniel turns the second key | ElevenLabs, AWS Bedrock |

Every case is one Arize Phoenix trace with three live evals: grounded, never asks for secrets, and right language.

## Run locally
```bash
cd backend && pip install -r requirements.txt && make mock     # :8000, all sponsors mocked
cd web && npm install && npm run dev                           # :3000
# open http://localhost:3000 and press a demo button
```

## Deploy
- **web/** goes to Vercel, with Root Directory `web` and env `NEXT_PUBLIC_API_URL`.
- **backend/** goes to Render (`render.yaml`, today) or AWS App Runner (`backend/Dockerfile`).

See `backend/README.md` for sponsor setup, smoke tests, and the event contract.
