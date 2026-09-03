// Temporary AT passthrough — USB <-> HC-05 SoftwareSerial
// Flash this, send AT commands from Python, then re-flash four_servos.ino
#include <SoftwareSerial.h>
SoftwareSerial btSerial(10, 11);
void setup() {
  Serial.begin(9600);
  btSerial.begin(9600);
}
void loop() {
  if (Serial.available())   btSerial.write(Serial.read());
  if (btSerial.available()) Serial.write(btSerial.read());
}
