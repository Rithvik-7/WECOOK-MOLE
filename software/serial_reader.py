from __future__ import annotations

import json
from typing import Any, Callable, Optional

import serial
from serial.tools import list_ports


class SerialReader:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None

    def open(self) -> None:
        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def read_obj(self) -> Optional[dict[str, Any]]:
        if self._ser is None:
            return None
        raw = self._ser.readline()
        if not raw:
            return None
        try:
            line = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            return None
        if not line:
            return None
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        return obj


def available_ports() -> list[dict[str, str]]:
    return [
        {
            "device": port.device,
            "description": port.description or "",
            "hwid": port.hwid or "",
        }
        for port in list_ports.comports()
    ]


def resolve_port(requested: str) -> str:
    if requested.lower() != "auto":
        return requested
    ports = available_ports()
    if not ports:
        raise RuntimeError("No serial ports found. Connect the S3-Zero by USB-C.")
    likely = [
        port for port in ports
        if any(
            token in (port["description"] + " " + port["hwid"]).lower()
            for token in ("esp32", "usb jtag", "usb serial", "303a:")
        )
    ]
    if len(likely) == 1:
        return likely[0]["device"]
    if len(ports) == 1:
        return ports[0]["device"]
    choices = ", ".join(
        f'{port["device"]} ({port["description"] or "unknown"})' for port in ports
    )
    raise RuntimeError(
        f"Could not choose one receiver automatically. Use --serial COMx. Found: {choices}"
    )


def ingest_loop(reader: SerialReader, on_obj: Callable[[dict[str, Any]], None], should_stop: Callable[[], bool]) -> None:
    while not should_stop():
        obj = reader.read_obj()
        if obj is not None:
            on_obj(obj)
