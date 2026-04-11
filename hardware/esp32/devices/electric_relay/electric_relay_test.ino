/*
 * ESP32 继电器测试代码 (Electric Relay Test)
 * 
 * 功能：每隔 2 秒切换一次继电器的状态（开启/关闭）
 * 用于硬件测试和验证接线。
 * 
 * 接线：
 * VCC -> ESP32 3.3V/5V
 * GND -> ESP32 GND
 * IN  -> ESP32 GPIO 18 (可调)
 */

#define RELAY_PIN 18  // 继电器信号线接 GPIO 18

// 继电器类型配置（大部分继电器模块是低电平触发）
#define RELAY_ACTIVE_LOW 1

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("  ESP32 继电器测试 (Electric Relay Test)");
  Serial.println("========================================");
  Serial.print("继电器引脚: ");
  Serial.println(RELAY_PIN);
  
  pinMode(RELAY_PIN, OUTPUT);
  
  // 初始状态：关闭继电器
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, HIGH);
  } else {
    digitalWrite(RELAY_PIN, LOW);
  }
  
  Serial.println("✓ 继电器已初始化，初始状态：OFF");
}

void loop() {
  // 开启继电器
  Serial.println(">>> 继电器状态：ON");
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, LOW);
  } else {
    digitalWrite(RELAY_PIN, HIGH);
  }
  delay(2000);
  
  // 关闭继电器
  Serial.println(">>> 继电器状态：OFF");
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, HIGH);
  } else {
    digitalWrite(RELAY_PIN, LOW);
  }
  delay(2000);
}
