/*
 * SG90 舵机 - 简化测试（不联网）
 * 串口输入 0-180 控制舵机角度
 *
 * 接线：信号线 → D5，VCC → 5V，GND → GND
 */

#include <Servo.h>

Servo myServo;
const int servoPin = D5;
int angle = 90;

void setup() {
  Serial.begin(115200);
  delay(500);
  myServo.attach(servoPin);
  myServo.write(angle);

  Serial.println(F("\n=== SG90 舵机测试 ==="));
  Serial.println(F("舵机=D4, 串口 115200"));
  Serial.println(F("输入 0-180 设置角度\n"));
}

void loop() {
  if (Serial.available()) {
    int val = Serial.parseInt();
    if (val >= 0 && val <= 180) {
      angle = val;
      myServo.write(angle);
      Serial.print(F("角度: "));
      Serial.print(angle);
      Serial.println(F("°"));
    }
  }
  delay(50);
}
