#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h> // 必须改为这个库

Adafruit_BMP280 bmp; // 实例化 bmp 对象

void setup() {
  Serial.begin(115200);
  
  // 明确指定引脚：D2=SDA, D1=SCL
  Wire.begin(4, 5);
  
  // 初始化，BMP280 地址通常也是 0x76
  if (!bmp.begin(0x76)) {
    Serial.println("初始化 BMP280 失败，请检查连线！");
    while (1);
  }
  
  Serial.println("BMP280 初始化成功！");
}

void loop() {
  Serial.print("温度: ");
  Serial.print(bmp.readTemperature());
  Serial.println(" *C");
  
  Serial.print("气压: ");
  Serial.print(bmp.readPressure() / 100.0F); // hPa
  Serial.println(" hPa");
  
  Serial.println("--------------------");
  delay(2000);
}