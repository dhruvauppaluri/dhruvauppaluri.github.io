/*
 * four_servos.ino — 4 LEDs + SH_BT_Board V1.3 (HC-05) @ 9600 baud
 *
 * ── LEDs ────────────────────────────────
 *   Pin 3 → 220Ω → LED1 (+) → GND
 *   Pin 5 → 220Ω → LED2 (+) → GND
 *   Pin 6 → 220Ω → LED3 (+) → GND
 *   Pin 9 → 220Ω → LED4 (+) → GND
 *
 * ── SH_BT_Board V1.3 (4 wires) ─────────
 *   VCC → 5V      GND → GND
 *   TXD → pin 10  RXD → pin 11 (1kΩ/2kΩ divider)
 *   STATE, KEY → leave empty
 *   Do NOT use pins 0/1 — those are USB.
 *
 * ── Commands (USB or Bluetooth) ─────────
 *   1-4   → LED on     !@#$  → LED off
 *   0     → all off    ?     → ping (OK)
 *
 * ── Mac usage ───────────────────────────
 *   pip3 install pyserial pynput
 *   python3 led_control.py --bluetooth
 */

#include <SoftwareSerial.h>

const uint8_t LED_PINS[]    = {3, 5, 6, 9};
const uint8_t BUTTON_PINS[] = {A0, A1, A2, A3};
const uint8_t BT_RX_PIN     = 10;
const uint8_t BT_TX_PIN     = 11;
const uint8_t LED_COUNT     = 4;

const char ON_KEYS[]  = {'1', '2', '3', '4'};
const char OFF_KEYS[] = {'!', '@', '#', '$'};

SoftwareSerial btSerial(BT_RX_PIN, BT_TX_PIN);
bool ledHeld[LED_COUNT];

void setLed(uint8_t i, bool on) {
  if (i < LED_COUNT) digitalWrite(LED_PINS[i], on ? HIGH : LOW);
}

void refreshLeds() {
  for (uint8_t i = 0; i < LED_COUNT; i++) {
    setLed(i, ledHeld[i] || digitalRead(BUTTON_PINS[i]) == LOW);
  }
}

void allOff(Stream &io) {
  for (uint8_t i = 0; i < LED_COUNT; i++) ledHeld[i] = false;
  refreshLeds();
  io.println(F("ALL OFF"));
}

void handleKey(char key, Stream &io) {
  if (key == '?') { io.println(F("OK")); return; }
  if (key == '0') { allOff(io); return; }

  for (uint8_t i = 0; i < LED_COUNT; i++) {
    if (key == ON_KEYS[i]) {
      ledHeld[i] = true;
      refreshLeds();
      io.print(F("LED ")); io.print(i + 1); io.println(F(" ON"));
      return;
    }
    if (key == OFF_KEYS[i]) {
      ledHeld[i] = false;
      refreshLeds();
      io.print(F("LED ")); io.print(i + 1); io.println(F(" OFF"));
      return;
    }
  }
}

void readStream(Stream &io) {
  while (io.available()) {
    char c = io.read();
    if (c != '\r' && c != '\n' && c != ' ')
      handleKey(c, io);
  }
}

void setup() {
  Serial.begin(9600);
  btSerial.begin(9600);

  for (uint8_t i = 0; i < LED_COUNT; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    pinMode(BUTTON_PINS[i], INPUT_PULLUP);
    ledHeld[i] = false;
  }
  refreshLeds();

  Serial.println(F("READY"));
  btSerial.println(F("READY"));
}

void loop() {
  refreshLeds();
  readStream(Serial);
  readStream(btSerial);
}
