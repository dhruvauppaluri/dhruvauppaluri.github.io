#!/usr/bin/env python3
"""
Mac LED control — USB or SH_BT_Board V1.3 Bluetooth (HC-05, 9600 baud).

Install once:   pip3 install pyserial pynput
Setup guide:    python3 led_control.py --setup
List ports:     python3 led_control.py --list
Test:           python3 led_control.py [--bluetooth] --test
Run:            python3 led_control.py [--bluetooth]

Keys: hold 1-4 = LED on, release = off.  0 = all off.  q = quit.
"""

import argparse
import platform
import sys
import time

if platform.system() != "Darwin":
    sys.exit("This script is for macOS only.")

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("Install pyserial:  pip3 install pyserial")

try:
    from pynput import keyboard
except ImportError:
    sys.exit("Install pynput:  pip3 install pynput")

BAUD = 9600
USB_RESET_DELAY = 2.0
BT_OPEN_DELAY = 3.0
PING_TIMEOUT = 4.0
OPEN_RETRIES = 3

BT_KEYWORDS = ("hc-05", "hc-06", "hc05", "hc06", "sh_bt", "sh-bt")
SKIP = ("bluetooth-incoming-port", "debug-console")

KEY_MAP = {
    "1": (b"1", b"!"),
    "2": (b"2", b"@"),
    "3": (b"3", b"#"),
    "4": (b"4", b"$"),
}


# ── Setup guide ──────────────────────────────────────────────────────────

def print_setup():
    print("""
================================================================
  SH_BT_Board V1.3 — Bluetooth setup on Mac
================================================================

STEP 1 — Wire the board (4 wires only)
---------------------------------------
  SH_BT_Board          Arduino Uno
  -----------          -----------
  VCC                  5V
  GND                  GND
  TXD                  pin 10   (NOT pin 0 or 1)
  RXD                  pin 11   (1k + 2k divider to GND)
  STATE                (skip)
  KEY                  (skip)

  LEDs: pins 3, 5, 6, 9 -> 220R -> LED (+) -> GND

STEP 2 — Upload firmware
-------------------------
  1. Open four_servos.ino in Arduino IDE
  2. Tools -> Board -> Arduino Uno
  3. Tools -> Port -> /dev/cu.usbmodem...
  4. Upload
  5. Close Serial Monitor and quit Arduino IDE

STEP 3 — Install Python packages (once)
-----------------------------------------
  pip3 install pyserial pynput

STEP 4 — Pair on Mac
----------------------
  1. Arduino plugged in (powers BT board)
  2. Board LED slow-blinks = ready to pair
  3. System Settings -> Bluetooth -> ON
  4. Click Connect on "HC-05"
  5. PIN: 1234  (if rejected: forget device, try 0000)
  6. Board LED fast-blinks = paired

STEP 5 — Verify port exists
-----------------------------
  python3 led_control.py --list

  Look for: /dev/cu.HC-05-...

STEP 6 — Test connection
--------------------------
  python3 led_control.py --bluetooth --test

  Success: "Connected (Bluetooth) ... Connection test passed."

STEP 7 — Run wireless control
-------------------------------
  python3 led_control.py --bluetooth

  Hold 1-4 = LED on.  Release = off.  0 = all off.  q = quit.

TROUBLESHOOTING
----------------
  Port won't open    -> Close Serial Monitor; one app per port
  No HC-05 in list   -> Re-pair in Bluetooth settings
  Test fails (no OK) -> Check TXD->10, RXD->11; re-upload sketch
  Keys don't work    -> System Settings -> Accessibility -> enable Terminal
""")


# ── Port helpers ─────────────────────────────────────────────────────────

def is_skipped(device):
    return any(s in device.lower() for s in SKIP)


def is_usb(device, desc=""):
    h = f"{device} {desc}".lower()
    return "usbmodem" in h or "usbserial" in h or "arduino" in h


def is_bt(device, desc=""):
    if is_skipped(device) or is_usb(device, desc):
        return False
    h = f"{device} {desc}".lower()
    return any(k in h for k in BT_KEYWORDS)


def all_ports():
    return [
        p for p in serial.tools.list_ports.comports()
        if p.device.startswith("/dev/cu.") and not is_skipped(p.device)
    ]


def find_usb():
    for p in all_ports():
        if is_usb(p.device, p.description or ""):
            return p.device
    return None


def find_bt_ports():
    return [p.device for p in all_ports() if is_bt(p.device, p.description or "")]


def find_bt():
    ports = find_bt_ports()
    return ports[0] if ports else None


def list_ports():
    print("Available serial ports:\n")
    ports = all_ports()
    if not ports:
        print("  (none found)")
        return
    for p in ports:
        tag = "USB" if is_usb(p.device, p.description or "") else (
              "BT " if is_bt(p.device, p.description or "") else "   ")
        print(f"  [{tag}]  {p.device}")
        if p.description:
            print(f"         {p.description}")


# ── Serial connection ────────────────────────────────────────────────────

def drain(ser, seconds=0.8):
    lines = []
    end = time.time() + seconds
    while time.time() < end:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            lines.append(line)
    return lines


def ping(ser):
    ser.reset_input_buffer()
    time.sleep(0.2)
    startup = drain(ser, 0.6)
    ser.write(b"?")
    ser.flush()
    deadline = time.time() + PING_TIMEOUT
    while time.time() < deadline:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line == "OK":
            return True, startup
        if line:
            startup.append(line)
    return False, startup


def open_port(port, bluetooth):
    last_err = None
    for n in range(1, OPEN_RETRIES + 1):
        try:
            ser = serial.Serial(port, BAUD, timeout=0.5)
            label = "Bluetooth" if bluetooth else "USB"
            print(f"Opening {label} port (try {n}/{OPEN_RETRIES})...")
            time.sleep(BT_OPEN_DELAY if bluetooth else USB_RESET_DELAY)
            return ser
        except serial.SerialException as e:
            last_err = e
            time.sleep(1.5)
    raise serial.SerialException(last_err)


def run_keys(ser):
    def on_press(key):
        try:
            c = key.char
        except AttributeError:
            return
        if c == "0":
            ser.write(b"0")
            ser.flush()
        elif c in KEY_MAP:
            ser.write(KEY_MAP[c][0])
            ser.flush()

    def on_release(key):
        try:
            c = key.char
        except AttributeError:
            return
        if c in KEY_MAP:
            ser.write(KEY_MAP[c][1])
            ser.flush()
        elif c == "q":
            return False

    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as lis:
            lis.join()
    except Exception:
        sys.exit(
            "\nKeyboard blocked.\n"
            "System Settings -> Privacy & Security -> Accessibility -> enable Terminal"
        )


def connect(port, bluetooth, test_only=False):
    if not port.startswith("/dev/cu."):
        print(f"Tip: on Mac use /dev/cu.* (not tty). Got: {port}")

    try:
        ser = open_port(port, bluetooth)
    except serial.SerialException as e:
        print(f"\nCould not open {port}:\n  {e}\n")
        if bluetooth:
            print("Close Serial Monitor, re-pair HC-05.")
            print("Full guide:  python3 led_control.py --setup")
        else:
            print("Close Serial Monitor and quit Arduino IDE.")
        sys.exit(1)

    with ser:
        ok, lines = ping(ser)
        mode = "Bluetooth" if bluetooth else "USB"

        if lines:
            print("Arduino:")
            for ln in lines:
                print(f"  {ln}")

        if not ok:
            print(f"\n  Opened {port} but got no OK reply.")
            print("  Check wiring (TXD->10, RXD->11) and re-upload four_servos.ino\n")
            print_setup()
            sys.exit(1)

        print(f"\n  Connected ({mode})  {port}  @ {BAUD} baud")

        if test_only:
            print("Connection test passed.")
            return

        print("\nHold 1-4 = on.  Release = off.  0 = all off.  q = quit.\n")
        run_keys(ser)


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Mac LED control — USB or SH_BT_Board V1.3")
    ap.add_argument("port", nargs="?", help="/dev/cu.HC-05-... or /dev/cu.usbmodem...")
    ap.add_argument("-b", "--bluetooth", action="store_true", help="Use paired HC-05")
    ap.add_argument("-l", "--list", action="store_true", help="List serial ports")
    ap.add_argument("-t", "--test", action="store_true", help="Test connection only")
    ap.add_argument("-s", "--setup", action="store_true", help="Print Bluetooth setup guide")
    args = ap.parse_args()

    if args.setup:
        print_setup()
        return

    if args.list:
        list_ports()
        return

    bt = args.bluetooth
    port = args.port or (find_bt() if bt else find_usb())

    if not port:
        print("No port found.\n")
        if bt:
            print_setup()
        else:
            print("Plug in Arduino, upload four_servos.ino, close Serial Monitor.")
            print("Then:  python3 led_control.py --test\n")
        list_ports()
        sys.exit(1)

    bt_ports = find_bt_ports()
    if bt and len(bt_ports) > 1 and not args.port:
        print("Multiple BT ports — using first. To pick one:")
        for p in bt_ports:
            print(f"  python3 led_control.py --bluetooth {p}")
        print()

    connect(port, bt, test_only=args.test)


if __name__ == "__main__":
    main()
