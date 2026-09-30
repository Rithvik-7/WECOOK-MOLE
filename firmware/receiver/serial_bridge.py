"""Read receiver USB lines and store them in the local gateway queue."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gateway"))
import gateway

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"


def stamp(packet):
    if packet.get("origin") == "physical" and not packet.get("sample_time"):
        packet["sample_time"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return packet


def main():
    import serial
    link = serial.Serial(PORT, 115200, timeout=1)
    print(f"reading {PORT}")
    while True:
        raw = link.readline().decode("utf-8", "replace").strip()
        if not raw.startswith("{"):
            continue
        packet = json.loads(raw)
        if packet.get("unit") == "receiver":
            print(raw)
            continue
        if "node_id" not in packet:
            continue
        gateway.enqueue(stamp(packet))
        print(gateway.sync())


if __name__ == "__main__":
    main()
