#!/usr/bin/env python3
"""
bt_daemon.py — persistent BLE/USB bridge for LED controller
- Maintains BLE connection to SH-HC-08 (HM-10) independent of web app
- Falls back to USB when BLE unavailable
- Auto-resets HM-10 via USB AT commands when BLE is stuck (>5 failures)
- WebSocket server on ws://localhost:8765
- Survives web app reloads and code edits
"""

import asyncio, json, logging, subprocess, sys, time
from pathlib import Path

import serial, serial.tools.list_ports
from bleak import BleakClient, BleakScanner
import websockets

# ── Config ────────────────────────────────────────────────────────────
BLE_NAMES     = {"SH-HC-08", "YOGI-BLE1", "HMSoft", "HM-10", "HMSoft_BLE"}
BLE_SVC       = "0000ffe0-0000-1000-8000-00805f9b34fb"
BLE_CHAR      = "0000ffe1-0000-1000-8000-00805f9b34fb"
WS_PORT       = 8765
BAUD          = 9600
SCAN_TIMEOUT  = 10.0
CONNECT_TIMEOUT = 12.0
ACLI          = "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"
FQBN          = "arduino:avr:uno"
SKETCH_LED    = str(Path(__file__).parent)
SKETCH_PASS   = str(Path(__file__).parent / "bt_passthrough")
USB_KEYWORDS  = ("usbmodem", "usbserial", "arduino")
SKIP_PORTS    = ("bluetooth-incoming-port", "debug-console")
AT_RESET_AFTER_FAILURES = 5

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/bt_daemon.log"),
    ]
)
log = logging.getLogger("btd")


# ── Helpers ───────────────────────────────────────────────────────────
def find_usb_port():
    for p in serial.tools.list_ports.comports():
        d = p.device
        if not d.startswith("/dev/cu."):
            continue
        if any(s in d.lower() for s in SKIP_PORTS):
            continue
        if any(k in d.lower() or k in (p.description or "").lower() for k in USB_KEYWORDS):
            return d
    return None


def is_ble_target(name: str | None) -> bool:
    if not name:
        return False
    return name in BLE_NAMES or "sh-hc" in name.lower() or "hm" in name.lower()


# ── Daemon ────────────────────────────────────────────────────────────
class Daemon:
    def __init__(self):
        self.mode         = "none"   # "ble" | "usb" | "none"
        self.ble_device   = None     # bleak BLEDevice
        self.ble_client   = None     # BleakClient (active)
        self.usb_ser      = None     # serial.Serial (reserve or active)
        self.ws_clients   = set()
        self.ble_failures = 0
        self._ble_task    = None
        self._stop        = asyncio.Event()

    # ── Status broadcast ─────────────────────────────────────────────
    async def broadcast(self, obj: dict):
        dead = set()
        msg  = json.dumps(obj)
        for ws in list(self.ws_clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self.ws_clients -= dead

    async def status(self, msg: str, submode: str | None = None):
        mode = submode or self.mode
        log.info("[%s] %s", mode, msg)
        await self.broadcast({"type": "status", "mode": mode,
                              "device": self.ble_device.name if self.ble_device else None,
                              "msg": msg})

    # ── Send command ─────────────────────────────────────────────────
    async def send_cmd(self, byte_val: int):
        data = bytes([byte_val])
        if self.mode == "ble" and self.ble_client and self.ble_client.is_connected:
            try:
                await self.ble_client.write_gatt_char(BLE_CHAR, data, response=False)
            except Exception as e:
                log.warning("BLE write error: %s", e)
        elif self.usb_ser and self.usb_ser.is_open:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: (self.usb_ser.write(data), self.usb_ser.flush()))
            except Exception as e:
                log.warning("USB write error: %s", e)

    # ── BLE notify callback ──────────────────────────────────────────
    def _on_ble_data(self, _sender, data: bytearray):
        text = data.decode("ascii", errors="ignore").strip()
        if text:
            asyncio.create_task(
                self.broadcast({"type": "data", "text": text}))

    def _on_ble_disconnect(self, client: BleakClient):
        log.warning("BLE link dropped")
        if self.mode == "ble":
            self.mode = "none"
        self.ble_client = None
        asyncio.create_task(self._ble_dropped())

    async def _ble_dropped(self):
        await self.status("BLE link lost — will reconnect", "none")
        # If USB is open, promote it immediately
        if self.usb_ser and self.usb_ser.is_open:
            self.mode = "usb"
            await self.status("switched to USB while BLE reconnects", "usb")

    # ── BLE scan + connect ───────────────────────────────────────────
    async def _scan_for_ble(self) -> "BLEDevice | None":
        log.info("BLE scan (%.0fs)…", SCAN_TIMEOUT)
        found = None

        def cb(device, adv):
            nonlocal found
            if found:
                return
            # Match by name OR by service UUID
            if is_ble_target(device.name):
                found = device
            elif adv.service_uuids and BLE_SVC in [u.lower() for u in adv.service_uuids]:
                found = device
                log.info("BLE found by service UUID: %s (%s)", device.name, device.address)

        async with BleakScanner(cb):
            deadline = asyncio.get_event_loop().time() + SCAN_TIMEOUT
            while not found and asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(0.2)

        if found:
            log.info("BLE found: %s @ %s", found.name, found.address)
        return found

    async def _connect_ble(self, device) -> bool:
        log.info("BLE connecting to %s…", device.name)
        try:
            client = BleakClient(
                device,
                disconnected_callback=self._on_ble_disconnect,
                timeout=CONNECT_TIMEOUT,
            )
            await client.connect()
            await client.start_notify(BLE_CHAR, self._on_ble_data)
            self.ble_client = client
            self.ble_device = device
            self.mode = "ble"
            self.ble_failures = 0
            await self.status(f"BLE connected to {device.name}", "ble")
            return True
        except Exception as e:
            log.warning("BLE connect failed: %s", e)
            try:
                await client.disconnect()
            except Exception:
                pass
            return False

    # ── AT reset via USB ─────────────────────────────────────────────
    async def _at_reset_via_usb(self):
        port = find_usb_port()
        if not port:
            log.warning("AT reset: no USB port available, skipping")
            return

        await self.status("resetting BLE module via USB AT commands…", "resetting")
        loop = asyncio.get_event_loop()

        def do_reset():
            # Close reserve USB handle if open
            if self.usb_ser:
                try: self.usb_ser.close()
                except Exception: pass
            self.usb_ser = None

            # Flash passthrough sketch
            log.info("Flashing passthrough sketch…")
            r = subprocess.run(
                [ACLI, "compile", "--fqbn", FQBN, SKETCH_PASS],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                log.error("compile failed: %s", r.stderr)
                return False
            r = subprocess.run(
                [ACLI, "upload", "--fqbn", FQBN, "--port", port, SKETCH_PASS],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                log.error("upload failed: %s", r.stderr)
                return False

            # Send AT commands
            time.sleep(2.5)
            try:
                s = serial.Serial(port, BAUD, timeout=2)
                time.sleep(1.0)
                s.reset_input_buffer()

                def at(cmd, wait=0.8):
                    s.write((cmd + "\r\n").encode()); s.flush()
                    time.sleep(wait)
                    resp = b""
                    deadline = time.time() + wait
                    while time.time() < deadline:
                        if s.in_waiting: resp += s.read(s.in_waiting)
                        time.sleep(0.05)
                    return resp.decode("ascii", errors="ignore").strip()

                r1 = at("AT")
                log.info("AT -> %r", r1)
                if "OK" in r1:
                    log.info("AT+RESET -> %r", at("AT+RESET"))
                    time.sleep(1.5)
                    # Re-check after reset
                    r2 = at("AT")
                    log.info("post-reset AT -> %r", r2)
                    if "OK" in r2:
                        log.info("AT+NAME? -> %r", at("AT+NAME?"))
                else:
                    log.warning("HM-10 not responding to AT in passthrough mode")
                s.close()
            except Exception as e:
                log.error("AT session error: %s", e)
                return False

            # Re-flash LED sketch
            log.info("Re-flashing LED sketch…")
            r = subprocess.run(
                [ACLI, "compile", "--fqbn", FQBN, SKETCH_LED],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                log.error("compile failed: %s", r.stderr)
                return False
            r = subprocess.run(
                [ACLI, "upload", "--fqbn", FQBN, "--port", port, SKETCH_LED],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                log.error("upload failed: %s", r.stderr)
                return False

            log.info("AT reset + reflash complete")
            return True

        ok = await loop.run_in_executor(None, do_reset)
        if ok:
            await self.status("BLE module reset complete, resuming scan…", "none")
            self.ble_failures = 0

    # ── BLE management loop ──────────────────────────────────────────
    async def ble_loop(self):
        backoff = 3.0
        while not self._stop.is_set():
            # Already connected
            if self.ble_client and self.ble_client.is_connected:
                await asyncio.sleep(1)
                continue

            # Clean up stale client
            if self.ble_client:
                try: await self.ble_client.disconnect()
                except Exception: pass
                self.ble_client = None

            # Auto-reset if too many failures and USB available
            if self.ble_failures >= AT_RESET_AFTER_FAILURES and find_usb_port():
                await self._at_reset_via_usb()
                backoff = 3.0

            await self.status(f"scanning… (failures: {self.ble_failures})", "scanning")
            device = await self._scan_for_ble()

            if not device:
                self.ble_failures += 1
                await self.status(f"not found (#{self.ble_failures}), retry in {backoff:.0f}s", "none")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 30.0)
                continue

            backoff = 3.0
            ok = await self._connect_ble(device)
            if not ok:
                self.ble_failures += 1
                await asyncio.sleep(5)

    # ── USB watcher loop ─────────────────────────────────────────────
    async def usb_loop(self):
        while not self._stop.is_set():
            port = find_usb_port()

            # Port appeared — open in reserve (or promote if BLE is down)
            if port and (self.usb_ser is None or not self.usb_ser.is_open):
                try:
                    ser = serial.Serial(port, BAUD, timeout=1)
                    await asyncio.sleep(2.0)
                    ser.reset_input_buffer()
                    ser.write(b"?"); ser.flush()
                    await asyncio.sleep(0.4)
                    resp = ser.readline().decode("ascii", errors="ignore").strip()
                    if resp == "OK":
                        self.usb_ser = ser
                        log.info("USB: Arduino live on %s", port)
                        if self.mode != "ble":
                            self.mode = "usb"
                            await self.status(f"USB connected on {port}", "usb")
                            asyncio.create_task(self._usb_read_loop())
                        else:
                            await self.broadcast({"type": "status", "mode": self.mode,
                                                  "usb_reserve": True,
                                                  "msg": f"USB available on {port} (BLE active)"})
                    else:
                        ser.close()
                except Exception as e:
                    log.warning("USB open error: %s", e)

            # Port gone
            elif not port and self.usb_ser:
                log.info("USB: port gone")
                try: self.usb_ser.close()
                except Exception: pass
                self.usb_ser = None
                if self.mode == "usb":
                    self.mode = "none"
                    await self.status("USB disconnected", "none")

            await asyncio.sleep(3)

    async def _usb_read_loop(self):
        buf = b""
        while self.usb_ser and self.usb_ser.is_open and self.mode == "usb":
            try:
                n = self.usb_ser.in_waiting
                if n:
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self.usb_ser.read(n))
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode("ascii", errors="ignore").strip()
                        if text:
                            await self.broadcast({"type": "data", "text": text})
                else:
                    await asyncio.sleep(0.05)
            except Exception as e:
                log.warning("USB read error: %s", e)
                break

    # ── WebSocket handler ────────────────────────────────────────────
    async def _handle_ws(self, ws):
        self.ws_clients.add(ws)
        log.info("WS client connected (%d total)", len(self.ws_clients))
        # Send current state immediately
        await ws.send(json.dumps({
            "type": "status", "mode": self.mode,
            "device": self.ble_device.name if self.ble_device else None,
            "msg": f"daemon running, mode={self.mode}"
        }))
        try:
            async for raw in ws:
                for c in raw.strip():
                    await self.send_cmd(ord(c))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.ws_clients.discard(ws)
            log.info("WS client disconnected (%d total)", len(self.ws_clients))

    # ── Entry point ──────────────────────────────────────────────────
    async def run(self):
        log.info("bt_daemon starting — ws://localhost:%d", WS_PORT)
        async with websockets.serve(self._handle_ws, "localhost", WS_PORT):
            await asyncio.gather(
                self.ble_loop(),
                self.usb_loop(),
            )


if __name__ == "__main__":
    try:
        asyncio.run(Daemon().run())
    except KeyboardInterrupt:
        log.info("bt_daemon stopped")
