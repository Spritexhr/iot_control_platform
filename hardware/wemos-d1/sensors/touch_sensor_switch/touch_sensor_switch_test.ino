/*
 * 触摸开关传感器 - 简化测试（不联网）
 * SIG 高电平=被触摸，低电平=未被触摸
 * 通过串口输出当前状态
 */

#define SIG_PIN D5
#define DEBOUNCE_MS 50

bool switchState = false;
bool lastPrintState = false;
unsigned long lastStableTime = 0;
unsigned long lastPrintTime = 0;

void setup() {
  Serial.begin(115200);
  pinMode(SIG_PIN, INPUT);
  switchState = (digitalRead(SIG_PIN) == HIGH);
  lastStableTime = millis();

  Serial.println(F("\n=== 触摸开关传感器 测试 ==="));
  Serial.println(F("SIG=D5, 串口 115200"));
  Serial.println(F("SIG高=被触摸, SIG低=未被触摸\n"));
}

void loop() {
  bool rawState = (digitalRead(SIG_PIN) == HIGH);
  unsigned long now = millis();

  // 防抖
  if (rawState != switchState && (now - lastStableTime >= DEBOUNCE_MS)) {
    switchState = rawState;
    lastStableTime = now;
  } else if (rawState == switchState) {
    lastStableTime = now;
  }

  // 状态变化时立即打印
  if (switchState != lastPrintState) {
    Serial.print(F("状态: "));
    Serial.println(switchState ? "被触摸" : "未被触摸");
    lastPrintState = switchState;
  }

  // 每 2 秒打印一次当前状态
  if (millis() - lastPrintTime >= 2000) {
    Serial.print(F("当前: "));
    Serial.println(switchState ? "被触摸" : "未被触摸");
    lastPrintTime = millis();
  }

  delay(5);
}
