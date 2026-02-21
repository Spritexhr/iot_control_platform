/*
 * 旋转传感器（模拟型） - 简化测试（不联网）
 *
 * 接线：OUT → A0，VCC → 3.3V，GND → GND
 * Wemos D1 Uno 仅 A0 支持模拟输入，电压范围 0~1V
 * 若传感器输出 >1V，请加分压或改用 3.3V 供电并确认规格
 *
 * 输出：原始值(0-1023) + 旋转位置(0-100%) + 角度(0-180°)
 */

const int sensorPin = A0;  // 传感器 OUT 连接至 A0（Wemos D1 唯一模拟输入）

void setup() {
  Serial.begin(115200);
  delay(500);  // ESP8266 串口稳定
  Serial.println(F("\n=== 旋转传感器（模拟型）测试 ==="));
  Serial.println(F("OUT=A0, VCC=3.3V, GND=GND"));
  Serial.println(F("输出: 原始值 | 位置% | 角度°\n"));
}

void loop() {
  int sensorValue = analogRead(sensorPin);  // 读取模拟值 0-1023

  // 映射为旋转位置 0-100%
  int positionPercent = map(sensorValue, 0, 1023, 0, 100);

  // 映射为角度 0-180°（可用于舵机控制）
  int angle = map(sensorValue, 0, 1023, 0, 180);

  Serial.print(F("传感器值: "));
  Serial.print(sensorValue);
  Serial.print(F(" | 位置: "));
  Serial.print(positionPercent);
  Serial.print(F("% | 角度: "));
  Serial.print(angle);
  Serial.println(F("°"));

  delay(100);  // 避免输出过快
}
