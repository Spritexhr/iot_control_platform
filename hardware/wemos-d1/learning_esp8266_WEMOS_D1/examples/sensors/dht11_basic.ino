#include <DHT.h>

// DHT11传感器配置
// 注意：D2 在 WEMOS D1 上对应 GPIO4
// 如果 D2 不工作，可以尝试其他引脚：D1(GPIO5), D5(GPIO14), D6(GPIO12), D7(GPIO13)
#define DHTPIN D2  // WEMOS D1 上的 D2 引脚 (GPIO4)
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  delay(1000);  // 增加延迟，确保串口初始化完成
  
  Serial.println(F("\n=== WEMOS D1 温湿度传感器调试 ==="));
  Serial.print(F("DHT传感器引脚: D2 (GPIO4)"));
  Serial.print(F(" | 传感器类型: DHT11"));
  Serial.println();
  
  // 初始化传感器
  dht.begin();
  Serial.println(F("✓ DHT传感器初始化完成"));
  
  // 等待传感器稳定（DHT11需要至少1秒）
  Serial.println(F("等待传感器稳定..."));
  delay(2000);
  
  // 测试读取
  Serial.println(F("开始测试读取..."));
}

void loop() {
  // 读取湿度（需要约250ms）
  float h = dht.readHumidity();
  
  // 读取温度（需要约250ms）
  float t = dht.readTemperature();
  
  // 检查读取是否成功
  if (isnan(h) || isnan(t)) {
    Serial.println(F("✗ DHT传感器读取失败！"));
    Serial.println(F("故障排除步骤："));
    Serial.println(F("1. 检查传感器连接："));
    Serial.println(F("   - VCC → 3.3V (或 5V)"));
    Serial.println(F("   - GND → GND"));
    Serial.println(F("   - DATA → D2 (GPIO4)"));
    Serial.println(F("   - DATA 和 VCC 之间需要 4.7K-10K 上拉电阻"));
    Serial.println(F("2. 检查传感器类型是否正确（DHT11 vs DHT22）"));
    Serial.println(F("3. 尝试更换引脚（如 D5, D6, D7）"));
    Serial.println(F("4. 检查供电是否稳定（至少 3.3V）"));
    Serial.println(F("5. 等待更长时间后重试（传感器需要稳定时间）"));
    Serial.println();
    delay(3000);  // 增加延迟，给传感器更多恢复时间
    return;
  }
  
  // 读取成功，显示数据
  Serial.print(F("✓ 读取成功 | "));
  Serial.print(F("湿度: "));
  Serial.print(h, 1);
  Serial.print(F(" % | 温度: "));
  Serial.print(t, 1);
  Serial.println(F(" °C"));

  delay(2000);
}

