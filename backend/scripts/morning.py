"""Morning start, one command:  python run.py morning [TEXT_BUDGET]

1. starts the Cloudflare tunnel to the backend port and waits for its public URL
2. writes PUBLIC_BASE_URL into .env.local (the URL changes every time the tunnel restarts)
3. points the Twilio number's SMS webhook at <url>/sms (API)
4. resets today's text counter and sets TEXT_BUDGET (default 55)
5. prints the two URLs you must paste by hand: the WhatsApp sandbox webhook and MacroDroid
then keeps the tunnel running in this window. Open two more windows for `python run.py dev` and `npm run dev`.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env.local"
PORT = os.environ.get("PORT", "8787")
CLOUDFLARED = next((p for p in [r"C:\Program Files (x86)\cloudflared\cloudflared.exe", r"C:\Program Files\cloudflared\cloudflared.exe", "cloudflared"] if p == "cloudflared" or Path(p).exists()), "cloudflared")


def set_env(key: str, value: str):
    s = ENV.read_text(encoding="utf-8")
    if re.search(rf"^{key}=", s, re.M):
        s = re.sub(rf"^{key}=.*$", f"{key}={value}", s, flags=re.M)
    else:
        s += f"\n{key}={value}\n"
    ENV.write_text(s, encoding="utf-8")


def main():
    budget = sys.argv[1] if len(sys.argv) > 1 else "55"
    print(f"[1/5] starting tunnel -> http://localhost:{PORT}")
    proc = subprocess.Popen([CLOUDFLARED, "tunnel", "--url", f"http://localhost:{PORT}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    url = None
    t0 = time.time()
    while time.time() - t0 < 60 and url is None:
        line = proc.stdout.readline()
        if not line:
            break
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            url = m.group(0)
    if not url:
        print("tunnel did not report a URL in 60 s. Is cloudflared installed? Try: cloudflared tunnel --url http://localhost:8787")
        proc.terminate()
        sys.exit(1)
    print(f"      public URL: {url}")

    print("[2/5] writing PUBLIC_BASE_URL, TEXT_BUDGET, DEMO_LIVE=0 into .env.local")
    set_env("PUBLIC_BASE_URL", url)
    set_env("TEXT_BUDGET", budget)
    set_env("DEMO_LIVE", "0")
    (ROOT / "data" / "texts_sent.json").write_text('{"sent": 0}', encoding="utf-8")

    print("[3/5] pointing the Twilio number's SMS webhook at the tunnel")
    sys.path.insert(0, str(ROOT))
    try:
        import httpx
        from app import config

        auth = (config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        base = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}"
        nums = httpx.get(f"{base}/IncomingPhoneNumbers.json", params={"PhoneNumber": config.TWILIO_FROM}, auth=auth, timeout=20).json().get("incoming_phone_numbers", [])
        if nums:
            r = httpx.post(f"{base}/IncomingPhoneNumbers/{nums[0]['sid']}.json", data={"SmsUrl": url + "/sms", "SmsMethod": "POST"}, auth=auth, timeout=20)
            print("      Twilio SMS webhook:", r.json().get("sms_url"))
        else:
            print("      Twilio number not found; set it in the console to", url + "/sms")
    except Exception as e:
        print("      Twilio update skipped:", e)

    print("[4/5] text budget today:", budget, "(sandbox WhatsApp quota; the screens show every text regardless)")
    print("[5/5] PASTE THESE BY HAND:")
    print(f"      WhatsApp sandbox  -> Twilio console -> Messaging -> Try it out -> Send a WhatsApp message -> Sandbox settings -> 'When a message comes in':\n         {url}/sms")
    print(f"      MacroDroid        -> Guardian macro -> HTTP Request -> URL:\n         {url}/ingest   (then turn the macro ON)")
    print()
    print("Now open two more windows:")
    print("   backend:  cd backend ; .\\.venv\\Scripts\\python.exe run.py dev")
    print("   web:      cd web ; npm run dev")
    print("Then open http://localhost:3000/stage, press P to check the family, play 1-4 in DEMO, and flip to LIVE only on stage.")
    print()
    print("Tunnel running. Keep this window open. Ctrl+C stops the tunnel (the URL changes if you restart it).")
    try:
        for line in proc.stdout:
            if "ERR" in line or "error" in line.lower():
                print(line.rstrip())
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
