# Contributing (team WE COOK)

This is a Smart India Hackathon 2026 hardware project (**SIH26025**). Read **[AGENTS.md](AGENTS.md)** before changing pins, radio, ML, dashboard copy, or the pitch.

## Rules of the road

1. Official ID is **SIH26025** only (never `SIH2026025`).
2. Do not invent boards, GPIOs, or a different radio path without updating `AGENTS.md` and `.cursor/rules/`.
3. Do not add camera, LoRa, login, cloud, CO ppm, collapse %, or autonomous drive.
4. Live USB failure must not fall back to simulation.
5. Isolation Forest cannot clear a latched rule. **Inspection done** is an operator action after recovery.
6. Prefer tests in `software/test_app.py` and `software/test_complete.py`.

## Run

```powershell
cd software
python -m pip install -r requirements.txt
python -m pytest -q
python app.py --mode simulate
```
