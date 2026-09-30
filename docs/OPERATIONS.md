# Operating MOLE locally

This copy is not on a public HTTPS address. Health reports `deployment: local` and `https: false`.

## Start

From the project root:

```powershell
python -m pip install -r api/requirements.txt httpx pytest
$env:MOLE_OPERATOR_TOKEN = "replace-with-a-long-random-token"
python -m uvicorn main:app --app-dir api --host 127.0.0.1 --port 8001
```

In a second terminal:

```powershell
cd web
npm install
$env:MOLE_API_INTERNAL = "http://127.0.0.1:8001"
npm run dev -- --port 3001
```

Open http://127.0.0.1:3001. The site loads without an account. Pair the browser with the same operator token before acknowledgement, closure, calibration, import commit, or rover notes. The token is not written into the website source.

The phone app source is in `mobile`. It is not an installed build. Push, SMS, and email are not configured.

## Check

```powershell
python -m pytest tests -q
node tests/test_stage7.mjs
python ml/benchmark.py
```

`GET /health` should show the database path and `ok: true` when that file exists.

## Backup and restore

Stop the API first so the database file is not mid-write.

```powershell
python -c "from scripts.backup import backup; from pathlib import Path; backup(Path('data/mole.db'), Path('data/evidence'), Path('backups/manual'))"
```

Restore only onto a database you can replace:

```powershell
python -c "from scripts.backup import restore; from pathlib import Path; restore(Path('backups/manual'), Path('data/mole.db'), Path('data/evidence'))"
```

The backup folder holds `mole.db`, `evidence`, and `manifest.json`. It is not encrypted and it is not an off-site copy.

## When something looks wrong

- The page says the service is unreachable: the API on port 8001 is stopped, or `MOLE_API_INTERNAL` points elsewhere.
- A paired action returns 403: the browser token and `MOLE_OPERATOR_TOKEN` differ, or the API was restarted without the token.
- A node looks normal after an old import: imported rows keep their own session and do not replace a newer live session.
- Rover controls do nothing: no controller is confirmed, so motion is refused.
- A PDF job fails: it stays in the job list and can be retried. The closure record remains.

## Still required before any public deployment

Do not buy a domain or start a hosted database until you choose to. The project needs, from you:

- A host, a domain, and a TLS certificate.
- A weather provider, an SMS or email provider, a push provider, and an LLM key, if those features should leave the local fallback.
- Exact boards, wiring, the IR module and its purpose, how many BME280 sensors exist, node positions, and the rover controller.

## Not claimed

No field certification. No trained Isolation Forest. No mesh. No flashed boards. No measured radio result. No rover motion. No rescue dispatch. Simulation and imported rows are labelled. Missing readings stay unavailable.
