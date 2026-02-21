# 版本对比：V1 vs V2

## 📊 核心差异对比表

| 特性 | V1 (temp_humi_upload.ino) | V2 (temp_humi_sensor_v2.ino) | 改进说明 |
|------|---------------------------|------------------------------|---------|
| **MQTT 主题格式** | `sensors/data` | `iot/sensors/{sensor_id}/data` | ✅ 符合 Model 设计 |
| **控制主题** | ❌ 无 | `iot/sensors/{sensor_id}/control` | ✅ 支持远程控制 |
| **状态主题** | ❌ 无 | `iot/sensors/{sensor_id}/status` | ✅ 运行状态监控 |
| **时间戳** | ❌ 无 | ✅ NTP 同步的准确时间戳 | ✅ 符合 Model 的 timestamp 字段 |
| **数据格式** | 嵌套复杂结构 | 扁平化的 data 对象 | ✅ 直接匹配 SensorData.data |
| **数据质量** | ❌ 无 | ✅ 自动计算质量分数 | ✅ 符合 quality_score 字段 |
| **硬件信息** | ❌ 无 | ✅ MAC、固件版本、信号强度 | ✅ 符合 Sensor Model 字段 |
| **远程控制** | ❌ 无 | ✅ 采集间隔、启用/禁用等 | ✅ 支持 mqtt_topic_control |
| **错误处理** | 基础检查 | 完善的验证和重试机制 | ✅ 提高可靠性 |
| **统计信息** | ❌ 无 | ✅ 成功率、失败次数等 | ✅ 便于运维监控 |

## 🔄 MQTT 主题对比

### V1 版本
```
发布主题: sensors/data
订阅主题: sensors/command  （功能未实现）
```

### V2 版本
```
发布主题: 
  - iot/sensors/DHT11-WEMOS-001/data      (数据上报)
  - iot/sensors/DHT11-WEMOS-001/status    (状态上报)
  
订阅主题:
  - iot/sensors/DHT11-WEMOS-001/control   (接收控制命令)
```

**改进点**：
- ✅ 主题包含 sensor_id，支持多设备
- ✅ 符合 Django Model 的 mqtt_topic_data 和 mqtt_topic_control 字段
- ✅ 便于后端使用通配符订阅：`iot/sensors/+/data`

## 📤 数据格式对比

### V1 版本数据格式
```json
{
  "sensor_name": "温湿度传感器",
  "sensor_id": "DHT11-WEMOS-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.0
  },
  "is_connected": true
}
```

**问题**：
- ❌ 包含冗余的 `sensor_name` 字段（后端已有）
- ❌ `is_connected` 字段意义不明确
- ❌ 缺少时间戳，后端只能用接收时间
- ❌ 缺少数据质量信息

### V2 版本数据格式
```json
{
  "sensor_id": "DHT11-WEMOS-001",
  "data": {
    "temperature": 25.5,
    "humidity": 60.0
  },
  "timestamp": 1706515200,
  "quality_score": 95,
  "is_valid": true,
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "firmware_version": "1.0.0",
  "hardware_version": "WEMOS_D1_R2",
  "rssi": -45
}
```

**改进**：
- ✅ 移除冗余字段
- ✅ 添加准确的时间戳（符合 SensorData.timestamp）
- ✅ 添加数据质量评分（符合 SensorData.quality_score）
- ✅ 添加硬件信息（符合 Sensor Model 字段）
- ✅ 添加 WiFi 信号强度（便于诊断）

## 🎛️ 功能对比

### V1 版本功能
- ✅ DHT11 数据读取
- ✅ WiFi 连接
- ✅ MQTT 发布
- ⚠️ 基础错误处理

### V2 版本功能
- ✅ DHT11 数据读取（改进的验证）
- ✅ WiFi 连接（自动重连）
- ✅ MQTT 发布（数据 + 状态）
- ✅ MQTT 订阅（接收控制命令）
- ✅ **NTP 时间同步**
- ✅ **数据质量评估系统**
- ✅ **远程控制功能**：
  - 动态调整采集间隔
  - 启用/禁用传感器
  - 获取实时状态
  - 重置统计数据
- ✅ **定期状态上报**（每5分钟）
- ✅ **完善的错误处理和重试**
- ✅ **运行统计信息**

## 📋 与 Django Model 的匹配度

### V1 版本
| Model 字段 | 是否支持 | 说明 |
|-----------|---------|------|
| sensor_id | ✅ | 支持 |
| mqtt_topic_data | ⚠️ | 格式不符 |
| mqtt_topic_control | ❌ | 未实现 |
| data | ⚠️ | 格式基本符合 |
| timestamp | ❌ | 无时间戳 |
| quality_score | ❌ | 无质量评分 |
| is_valid | ❌ | 无验证标记 |
| mac_address | ❌ | 无硬件信息 |
| firmware_version | ❌ | 无版本信息 |
| sampling_interval | ⚠️ | 硬编码，不可控 |

**匹配度**: 约 40%

### V2 版本
| Model 字段 | 是否支持 | 说明 |
|-----------|---------|------|
| sensor_id | ✅ | 完全支持 |
| mqtt_topic_data | ✅ | 格式完全符合 |
| mqtt_topic_control | ✅ | 完全实现 |
| data | ✅ | 格式完全符合 |
| timestamp | ✅ | NTP 同步时间戳 |
| quality_score | ✅ | 自动计算 |
| is_valid | ✅ | 数据验证 |
| mac_address | ✅ | 自动获取 |
| firmware_version | ✅ | 内置版本号 |
| sampling_interval | ✅ | 可远程调整 |

**匹配度**: 100% ✨

## 🔧 代码质量对比

### V1 版本
- 代码行数: ~196 行
- 功能模块: 基础功能
- 配置灵活性: 低（硬编码）
- 错误处理: 基础
- 可维护性: 中等

### V2 版本
- 代码行数: ~460 行
- 功能模块: 完整功能
- 配置灵活性: 高（可远程控制）
- 错误处理: 完善
- 可维护性: 高
- 代码结构: 模块化、注释完善

## 📈 性能对比

| 指标 | V1 | V2 | 说明 |
|-----|----|----|------|
| 默认采集间隔 | 5秒 | 60秒 | V2 更合理，可远程调整 |
| 数据包大小 | ~150 字节 | ~250-350 字节 | V2 包含更多有用信息 |
| 内存占用 | 较低 | 中等 | V2 使用 ArduinoJson |
| CPU 占用 | 低 | 低 | 两者都很低 |
| 网络流量 | 少 | 中等 | V2 可通过调整间隔控制 |

## 🚀 升级建议

### 推荐使用 V2 的场景：
1. ✅ 生产环境部署
2. ✅ 需要远程运维管理
3. ✅ 需要数据质量监控
4. ✅ 多传感器规模化部署
5. ✅ 需要准确的时间戳
6. ✅ 需要硬件信息追踪

### 可继续使用 V1 的场景：
1. ⚠️ 仅用于测试和学习
2. ⚠️ 内存极度受限的场景
3. ⚠️ 不需要高级功能

## 📦 所需额外库（V2）

V2 版本需要额外安装以下库：
- `NTPClient` - NTP 时间同步
- `ArduinoJson` - JSON 序列化/反序列化

这些都是稳定、广泛使用的标准库。

## 🔄 迁移步骤

从 V1 迁移到 V2：

1. **安装所需库**
   ```
   Arduino IDE -> 工具 -> 管理库
   搜索并安装: NTPClient, ArduinoJson
   ```

2. **更新固件配置**
   - 修改 WiFi 和 MQTT 配置
   - 为每个设备设置唯一的 sensor_id

3. **更新 Django 后端**
   - 更新 MQTT 订阅主题：`iot/sensors/+/data`
   - 修改数据解析逻辑（参考 README_V2.md）

4. **上传固件**
   - 上传 temp_humi_sensor_v2.ino
   - 通过串口监视器验证运行

5. **测试验证**
   - 检查数据上报
   - 测试控制命令
   - 验证时间戳准确性

## 📊 兼容性说明

**后端兼容性**：
- V1 和 V2 的数据格式不完全兼容
- 需要更新后端的 MQTT 消息处理逻辑
- 建议统一使用 V2 格式

**共存方案**：
- 可以让 V1 和 V2 设备共存
- 后端根据 MQTT 主题格式区分版本
- 逐步将 V1 设备升级到 V2

## 🎯 总结

V2 版本是完全基于 Django Model 设计的生产级固件，提供了：
- ✅ 100% Model 匹配度
- ✅ 完整的远程控制能力
- ✅ 专业的数据质量管理
- ✅ 可靠的运行监控
- ✅ 便于维护和扩展

**强烈推荐使用 V2 版本进行实际部署！** 🎉
