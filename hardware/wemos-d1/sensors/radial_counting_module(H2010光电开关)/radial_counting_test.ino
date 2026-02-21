/*
 * H2010 光电开关 - 简化测试（不联网）
 * 仅读取 OUT 引脚脉冲并计数，通过串口输出
 */

#define OUT_PIN D5

volatile unsigned long pulseCount = 0;
bool lastOutState = false;
unsigned long lastPrintTime = 0;

void setup() {
  Serial.begin(115200);
  pinMode(OUT_PIN, INPUT);
  lastOutState = (digitalRead(OUT_PIN) == HIGH);

  Serial.println(F("\n=== H2010 光电开关 测试 ==="));
  Serial.println(F("OUT=D5, 串口 115200"));
  Serial.println(F("有物体通过时计数值增加\n"));
}

void loop() {
  bool curr = (digitalRead(OUT_PIN) == HIGH);
  if (curr && !lastOutState) {
    pulseCount++;
  }
  lastOutState = curr;

  // 每 2 秒打印一次
  if (millis() - lastPrintTime >= 2000) {
    Serial.print(F("计数: "));
    Serial.println(pulseCount);
    lastPrintTime = millis();
  }

  delay(5);
}
