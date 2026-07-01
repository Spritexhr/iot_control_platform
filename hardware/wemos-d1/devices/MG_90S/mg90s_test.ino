/*
 * MG90S 金属舵机 - 简化测试（不联网）
 * 串口输入 0-180 控制舵机角度
 *
 * 接线：信号线 → D5，VCC → 5V（建议外部供电，并与开发板共地），GND → GND
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

  Serial.println(F("\n=== TowerPro MG90S 金属舵机测试 ==="));
  Serial.println(F("舵机引脚: D5 (GPIO14), 串口波特率: 115200"));
  Serial.println(F("注意: 金属舵机工作电流较大，建议使用外部5V电源供电，并与开发板共地"));
  Serial.println(F("输入 0-180 并发送以设置舵机角度\n"));
}

void loop() {
  if (Serial.available()) {
    int val = Serial.parseInt();
    if (val >= 0 && val <= 180) {
      angle = val;
      myServo.write(angle);
      Serial.print(F("设置角度: "));
      Serial.print(angle);
      Serial.println(F("°"));
    }
  }
  delay(50);
}
