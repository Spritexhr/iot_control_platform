# Luyben 乙苯全厂控制详细实施方案

> 文档版本：1.0  
> 日期：2026-06-29  
> 实施状态：基础数据、成员、视图入口、ControlScheme 和 AutomationRule 已通过 Docker 中的 Django shell 创建到运行库 MySQL；所有控制默认停用。  
> 适用范围：现有 `EB` Project 中的 `01 制乙苯车间`和`02 乙苯分离车间`。  
> 文献依据：William L. Luyben, *Design and Control of the Ethyl Benzene Process*, AIChE Journal, 57(3), 655-670, 2011, DOI: 10.1002/aic.12289。  
> 本系统用于教学模拟，不面向真实化工生产。

## 一、实施结论

本方案在现有通用 Project 架构内复现 Luyben 乙苯控制结构，目标为 L1：

- 设备、物流、测点、控制器和控制关系能够在系统中配置；
- P/PI/PID 使用现有 `ControlScheme`；
- P-only 使用 PI 且 `Ki=0`；
- 总苯比值、R/F 和 VPC 使用 `AutomationRule`；
- P&ID 在现有 Project 画板中补充；
- 不建立动态机理模型；
- 不验证论文动态响应曲线；
- 不恢复已废弃的 `eb_plant` 插件；
- 不修改 `Sensor`、`Device` 主模型；
- 不增加脚本冲突或执行器占用校验。

本次没有新建 `EB-LUYBEN` Project。运行库已经存在：

```text
Project EB：苯乙烯生产工厂
├── 01 制乙苯车间       ← Luyben 反应与进料部分
├── 02 乙苯分离车间     ← Luyben C1/C2 分离部分
├── 03 制苯乙烯车间     ← 不在本方案范围
└── 04 苯乙烯分离车间   ← 不在本方案范围
```

Luyben 乙苯流程正好是现有苯乙烯工厂的前两段，因此直接复用 `EB` Project 是最清晰的做法。

## 二、四位仪表编号规则

### 2.1 编号格式

所有仪表和控制器采用：

```text
仪表前缀 + 四位号码
```

例如：

```text
PI0101
│ │ └─ 01：该类仪表在本车间内的流程顺序
│ └─── 01：1 号车间
└───── PI：压力指示仪表
```

编号中不使用短横线，所以使用 `PI0101`，不使用 `PI-0101`。

### 2.2 前两位：车间编号

| 编号 | 车间 | 本方案用途 |
|---|---|---|
| `01` | 制乙苯车间 | 原料、R1、DEB 回流混合、R2 |
| `02` | 乙苯分离车间 | C1 苯回收、C2 乙苯精制 |
| `03` | 制苯乙烯车间 | 不在本方案范围 |
| `04` | 苯乙烯分离车间 | 不在本方案范围 |

### 2.3 后两位：按物料方向排序

后两位按物料从装置入口到出口的顺序排列。01 车间现有 P&ID 已经使用了这种顺序，本方案予以保留：

| 号码 | 物流位置 | 对应仪表组 |
|---|---|---|
| `0101` | C1 塔顶循环苯返回 R1 | `FI0101`、`PI0101`、`TI0101` |
| `0102` | 新鲜苯进料 | `FI0102`、`PI0102`、`TI0102` |
| `0103` | 新鲜乙烯进料 | `FI0103`、`PI0103`、`TI0103` |
| `0104` | R1 出口至 R2 | `FI0104`、`PI0104`、`TI0104` |
| `0105` | C2 塔底 DEB 回流至 R2 | `FI0105`、`PI0105`、`TI0105` |
| `0106` | R2 出口至 C1 | `FI0106`、`PI0106`、`TI0106` |
| `0107` | R1 蒸汽移热辅助系统 | `PI0107`、`PIC0107` |

02 车间继续沿物料方向编号：

| 号码 | 物流或设备位置 |
|---|---|
| `0201` | C1 进料/C1 主控制组 |
| `0202` | C1 回流及 C2 主控制组（不同前缀分别排序） |
| `0203` | C1 塔顶循环苯或 C2 塔釜液位 |
| `0204` | C1 塔底至 C2 或 C2 回流罐液位 |
| `0205` | C2 回流 |
| `0206` | C2 塔顶 EB 产品 |
| `0207` | C2 塔底 DEB 回流 |

同一物流上的不同测量量共用四位号码。例如循环苯物流使用 `FI0101`、`PI0101`、`TI0101`。同一控制回路尽量沿用测点号码，例如：

```text
FI0103 → FIC0103 → FV0103
TI0104 → TIC0104 → PIC0107
PI0201 → PIC0201 → PV0201
```

### 2.4 前缀含义

| 前缀 | 含义 |
|---|---|
| `FI` | 流量指示/测量 |
| `FIC` | 流量指示控制器 |
| `FRC` | 流量比值控制器 |
| `PI` | 压力指示/测量 |
| `PIC` | 压力指示控制器或压力控制器设定值接口 |
| `TI` | 温度指示/测量 |
| `TIC` | 温度指示控制器 |
| `LI` | 液位指示/测量 |
| `LIC` | 液位指示控制器 |
| `AI` | 组分分析指示 |
| `VPC` | 阀位/协调控制器 |
| `FV` | 流量调节阀 |
| `PV` | 压力或冷凝负荷执行器 |
| `TV` | 温度或再沸器热负荷执行器 |
| `LV` | 液位调节阀 |

## 三、Luyben 流程和控制目标

### 3.1 反应网络

论文采用三条反应：

1. 乙烯 + 苯 → 乙苯（EB）；
2. 乙烯 + 乙苯 → 二乙苯（DEB）；
3. DEB + 苯 → 2 EB。

低乙烯浓度和较低反应温度有利于减少 DEB。C2 塔底 DEB 返回 R2，与苯继续反应，形成 recycle to extinction。

### 3.2 工艺设备

| 设备 | 作用 |
|---|---|
| R1 | 乙烯与过量苯反应；通过产生低压蒸汽移热 |
| R2 | 接收 R1 出料和 DEB 回流，将 DEB 转为 EB |
| C1 | 塔顶回收苯并返回 R1，塔底 EB/DEB 进入 C2 |
| C2 | 塔顶得到 EB 产品，塔底 DEB 返回 R2 |

### 3.3 论文基准值

| 项目 | 论文值 | 本系统用途 |
|---|---:|---|
| 新鲜乙烯 | 630.6 kmol/h | `FI0103` 正常值、`FIC0103` SP |
| 新鲜苯 | 630.6 kmol/h | `FI0102` 正常值 |
| 循环苯 | 969.4 kmol/h | `FI0101` 正常值 |
| 总苯 | 1600 kmol/h | FRC 计算参考 |
| R1 温度 | 433.7 K | `TIC0104` SP |
| R1 压力 | 约 20 atm | `PI0104` 正常值 |
| R2 温度 | 约 432 K | `TI0106` 正常值 |
| R2 压力 | 约 19 atm | `PI0106` 正常值 |
| C1 压力 | 0.3 atm | `PIC0201` SP |
| C1 第 14 级温度 | 365.8 K | `TIC0201` SP |
| C2 压力 | 0.1 atm | `PIC0202` SP |
| C2 第 20 级温度 | 394.5 K | `TIC0202` SP |
| EB 产品 | 630.6 kmol/h，99.9 mol% | `FI0206`、`AI0201` 正常值 |
| DEB 回流 B2 | 251.2 kmol/h | `FI0105`/`FI0207`、VPC SP |

论文流程图中的 Aspen Plus B2 为 282.2 kmol/h；控制器表 7 使用动态控制基准 251.2 kmol/h。本方案的 VPC 使用 251.2。

## 四、已创建的传感器

### 4.1 01 制乙苯车间

原运行库已有 `FI/PI/TI0101-0106` 和 `LI0101`。本次保留 ID，补全了详细描述和 Project member 元数据；新增 `LI0102`、`PI0107`、`AI0101`。

| ID | data_key | 单位 | 工艺含义 | 正常值 |
|---|---|---|---|---:|
| `FI0101` | `flow_rate` | kmol/h | C1 循环苯返回 R1 | 969.4 |
| `PI0101` | `pressure` | atm | 循环苯压力 | - |
| `TI0101` | `temperature` | K | 循环苯温度 | - |
| `FI0102` | `flow_rate` | kmol/h | 新鲜苯流量 | 630.6 |
| `PI0102` | `pressure` | atm | 新鲜苯压力 | - |
| `TI0102` | `temperature` | K | 新鲜苯温度 | 320 |
| `FI0103` | `flow_rate` | kmol/h | 新鲜乙烯流量 | 630.6 |
| `PI0103` | `pressure` | atm | 新鲜乙烯压力 | - |
| `TI0103` | `temperature` | K | 新鲜乙烯温度 | 320 |
| `FI0104` | `flow_rate` | kmol/h | R1 出口流量 | 1696 |
| `PI0104` | `pressure` | atm | R1 出口压力 | 20 |
| `TI0104` | `temperature` | K | R1 出口温度，R1 温度回路 PV | 433.7 |
| `FI0105` | `flow_rate` | kmol/h | DEB 回流至 R2，VPC PV | 251.2 |
| `PI0105` | `pressure` | atm | DEB 回流压力 | - |
| `TI0105` | `temperature` | K | DEB 回流温度 | - |
| `FI0106` | `flow_rate` | kmol/h | R2 出口至 C1 | 1882 |
| `PI0106` | `pressure` | atm | R2 出口压力 | 19 |
| `TI0106` | `temperature` | K | R2 出口温度 | 432 |
| `LI0101` | `level` | % | R1 液位 | 50 |
| `LI0102` | `level` | % | R2 液位 | 50 |
| `PI0107` | `pressure` | atm | R1 移热蒸汽系统压力 | 2.5 |
| `AI0101` | `deb_mol_fraction` | mol fraction | 新鲜苯中 DEB 组分 | 0 |

现有 FI 类型还有 `accumulated_volume` 字段。Luyben 控制只使用 `flow_rate`，所以 01 车间六个 FI 的累计量成员已隐藏但未删除。

### 4.2 02 乙苯分离车间

| ID | data_key | 单位 | 工艺含义 | 正常值 |
|---|---|---|---|---:|
| `FI0201` | `flow_rate` | kmol/h | C1 进料 | 1882 |
| `FI0202` | `flow_rate` | kmol/h | C1 回流 | 待模拟配置 |
| `FI0203` | `flow_rate` | kmol/h | C1 塔顶循环苯 | 969.4 |
| `FI0204` | `flow_rate` | kmol/h | C1 塔底至 C2 | 912.8 |
| `FI0205` | `flow_rate` | kmol/h | C2 回流 | 待模拟配置 |
| `FI0206` | `flow_rate` | kmol/h | C2 塔顶 EB 产品 | 630.6 |
| `FI0207` | `flow_rate` | kmol/h | C2 塔底 DEB 回流 B2 | 251.2 |
| `PI0201` | `pressure` | atm | C1 塔顶压力 | 0.3 |
| `PI0202` | `pressure` | atm | C2 塔顶压力 | 0.1 |
| `TI0201` | `temperature` | K | C1 第 14 级温度 | 365.8 |
| `TI0202` | `temperature` | K | C2 第 20 级温度 | 394.5 |
| `LI0201` | `level` | % | C1 塔釜液位 | 50 |
| `LI0202` | `level` | % | C1 回流罐液位 | 50 |
| `LI0203` | `level` | % | C2 塔釜液位 | 50 |
| `LI0204` | `level` | % | C2 回流罐液位 | 50 |
| `AI0201` | `eb_mol_fraction` | mol fraction | EB 产品纯度 | 0.999 |

### 4.3 MQTT 主题

所有新 Sensor 沿用主模型自动主题：

```text
iot/sensors/<Sensor ID>/data
iot/sensors/<Sensor ID>/control
```

例如：

```text
iot/sensors/TI0201/data
iot/sensors/TI0201/control
```

上报 payload 中必须使用表中的 data_key。例如 `TI0201` 应上报：

```json
{"temperature": 365.8}
```

## 五、已创建的执行器

### 5.1 01 制乙苯车间

| Device ID | 类型 | 命令 | 作用 |
|---|---|---|---|
| `FV0102` | 流量调节阀 | `set_opening(val)` | 新鲜苯调节阀 |
| `FV0103` | 流量调节阀 | `set_opening(val)` | 新鲜乙烯调节阀 |
| `LV0101` | 液位调节阀 | `set_opening(val)` | R1 出口阀 |
| `LV0102` | 液位调节阀 | `set_opening(val)` | R2 出口阀 |
| `PIC0107` | 设定值接口 | `set_setpoint(val)` | 蒸汽压力内环设定值接口 |

### 5.2 02 乙苯分离车间

| Device ID | 命令 | 作用 |
|---|---|---|
| `PV0201` | `set_duty(val)` | C1 冷凝负荷/塔压执行器 |
| `LV0201` | `set_opening(val)` | C1 塔底出料阀 |
| `LV0202` | `set_opening(val)` | C1 塔顶循环苯出料阀 |
| `TV0201` | `set_duty(val)` | C1 再沸器热负荷 |
| `FV0202` | `set_opening(val)` | C1 回流阀 |
| `PV0202` | `set_duty(val)` | C2 冷凝负荷/塔压执行器 |
| `LV0203` | `set_opening(val)` | C2 塔底 DEB 回流阀 |
| `LV0204` | `set_opening(val)` | C2 塔顶 EB 产品阀 |
| `TV0202` | `set_duty(val)` | C2 再沸器热负荷 |
| `FV0205` | `set_opening(val)` | C2 回流阀 |

Device 自动使用：

```text
iot/devices/<Device ID>/status
iot/devices/<Device ID>/control
```

模拟设备收到命令后应回传带相同 `check_code` 的状态，否则平台会在 3 秒后认为命令未确认。

## 六、已创建的 ControlScheme

所有方案均为：

```text
is_enabled = false
status = idle
```

不会在创建后自动下发命令。

### 6.1 01 车间

| 名称 | PV | SP | MV | 类型 | 关键参数 |
|---|---|---:|---|---|---|
| `FIC0103 新鲜乙烯流量控制` | `FI0103.flow_rate` | 630.6 | `FV0103.set_opening` | PI | Kp=0.1，Ki=0.001，教学初值 |
| `LIC0101 R1 液位控制` | `LI0101.level` | 50% | `LV0101.set_opening` | P | PI 模板，Kp=5，Ki=0 |
| `TIC0104 R1 温度控制` | `TI0104.temperature` | 433.7 K | `PIC0107.set_setpoint` | PI | Kp=1.5，Ki=0.0009615；输出 350-450 K |
| `LIC0102 R2 液位控制` | `LI0102.level` | 50% | `LV0102.set_opening` | P | PI 模板，Kp=5，Ki=0 |

`TIC0104` 对应论文的串级结构：R1 温度外环不直接控制蒸汽阀，而是给蒸汽压力控制器写设定值。本系统用 Device `PIC0107` 表示这个内环接口。

### 6.2 02 车间

| 名称 | PV | SP | MV | 类型 | 关键参数 |
|---|---|---:|---|---|---|
| `PIC0201 C1 塔压控制` | `PI0201.pressure` | 0.3 atm | `PV0201.set_duty` | PI | Kp=100，Ki=1，教学初值 |
| `LIC0201 C1 塔釜液位控制` | `LI0201.level` | 50% | `LV0201.set_opening` | P | Kp=2，Ki=0 |
| `LIC0202 C1 回流罐液位控制` | `LI0202.level` | 50% | `LV0202.set_opening` | P | Kp=2，Ki=0 |
| `TIC0201 C1 第14级温度控制` | `TI0201.temperature` | 365.8 K | `TV0201.set_duty` | PI | Kp=0.54，Ki=0.0006923；0-6.6×10⁶ cal/s |
| `PIC0202 C2 塔压控制` | `PI0202.pressure` | 0.1 atm | `PV0202.set_duty` | PI | Kp=100，Ki=1，教学初值 |
| `LIC0203 C2 塔釜液位控制` | `LI0203.level` | 50% | `LV0203.set_opening` | P | Kp=2，Ki=0 |
| `LIC0204 C2 回流罐液位控制` | `LI0204.level` | 50% | `LV0204.set_opening` | P | Kp=2，Ki=0 |
| `TIC0202 C2 第20级温度控制` | `TI0202.temperature` | 394.5 K | `TV0202.set_duty` | PI | Kp=1.5，Ki=0.0027174；0-6.6×10⁶ cal/s |

### 6.3 参数来源

论文表 7 给出温度回路参数：

| 回路 | Kc | τI |
|---|---:|---:|
| R1 TIC | 1.5 | 26 min |
| C1 第 14 级 TIC | 0.54 | 13 min |
| C2 第 20 级 TIC | 1.5 | 9.2 min |

当前控制器按秒积分，换算为：

```text
Kp = Kc × 100 / PV_span
Ki = Kp / (τI × 60)
```

论文没有提供流量和塔压回路的完整整定值，所以 `FIC0103`、`PIC0201`、`PIC0202` 使用停用状态的教学初值。启用前可由用户在控制页面调整。

## 七、已创建的 AutomationRule

所有脚本均为：

```text
is_launched = false
process_status = idle
poll_interval = 5 s
```

### 7.1 FRC0102 + VPC0101

名称：

```text
FRC0102 总苯/乙烯比值与 VPC0101 协调控制
```

script_id：

```text
frc0102_benzene_ratio_vpc
```

输入：

- `FI0101` 循环苯；
- `FI0102` 新鲜苯；
- `FI0103` 新鲜乙烯；
- `FI0105` DEB 回流 B2。

输出：

- `FV0102` 新鲜苯阀。

固定比值结构：

```text
BTOT = FI0101 + FI0102
BTOT_SP = 2.537 × FI0103
```

VPC 修正：

```text
ratio = clamp(0, 5, 2.537 + 0.006 × (FI0105 - 251.2))
BTOT_SP = ratio × FI0103
```

脚本将总苯流量 P 控制合并在同一规则内：

```text
FV0102 opening = clamp(0, 100, 50 + 0.05 × (BTOT_SP - BTOT))
```

`0.05` 和输出偏置 `50` 是教学初值，不是论文给出的流量控制器参数。

### 7.2 FRC0201：C1 R/F

script_id：`frc0201_c1_reflux_feed_ratio`

```text
C1 reflux SP = 0.4332 × FI0201
MV = FV0202
```

0.4332 来自论文表 6 的 C1 基准 R/F。

### 7.3 FRC0202：C2 R/F

script_id：`frc0202_c2_reflux_feed_ratio`

```text
C2 reflux SP = 0.4582 × FI0204
MV = FV0205
```

0.4582 来自论文表 6 的 C2 基准 R/F。

### 7.4 脚本责任边界

平台不检查多个规则是否驱动同一 Device。操作者必须自行保证：

- 启动 `FRC0102` 时，不同时启用其他直接驱动 `FV0102` 的方案；
- 启动 `FRC0201` 时，不同时启用其他直接驱动 `FV0202` 的方案；
- 启动 `FRC0202` 时，不同时启用其他直接驱动 `FV0205` 的方案；
- 修改脚本后先使用单次执行观察输出，再启动轮询。

## 八、P&ID 画板文字设计

本章只描述前端画板应如何绘制，不提供 Vue、Vue Flow 或 JSON 代码。

### 8.1 通用画板约定

#### 物流线

- 使用黑色或工程蓝实线；
- 箭头必须与物料方向一致；
- 主管线略粗，回流支线略细；
- 在线旁标注主要物流名：循环苯、新鲜苯、新鲜乙烯、R1 出料、DEB 回流、EB 产品；
- C1 循环苯回流和 C2 DEB 回流应使用明显的长回路连线。

#### 控制信号线

- 使用红色虚线；
- Sensor/仪表 → Controller；
- Controller → Device；
- 比值和 VPC 的多输入线汇入同一个控制器框；
- 控制线不得与物料线使用相同样式。

#### 节点显示

- Sensor 圆形仪表节点显示仪表 ID 和实时值；
- Controller 使用带前缀的圆角矩形或控制器气泡；
- Device 显示阀门或热负荷符号并绑定 Device ID；
- 设备节点显示名称，仪表节点只显示简洁 ID；
- 详细说明放在 tooltip/侧栏，不把长描述塞进画布。

#### 单位

- 流量：kmol/h；
- 温度：K；
- 压力：atm；
- 液位、开度：%；
- 组分：mol fraction；
- 再沸器/冷凝器负荷：cal/s 或经过统一换算的工程单位。

### 8.2 01 制乙苯车间画板布局

01 车间现有 P&ID 已经包含三条进料、两个混合点和两台反应器，应在现有画板上补充和校正，不要重做整页。

#### 第一层：苯进料

画布左上布置两条平行物流：

1. 循环苯入口；
2. 新鲜苯入口。

循环苯线按物料方向排列：

```text
循环苯入口 → PI0101 → FI0101 → TI0101 ┐
                                           ├→ M0101 → R1
新鲜苯入口 → PI0102 → FI0102 → TI0102 ┘
```

在 `FI0102/FI0101/FI0103/FI0105` 附近布置 `FRC0102 + VPC0101` 控制块：

- `FI0101`、`FI0102` 合成总苯；
- `FI0103` 提供新鲜乙烯流量；
- `FI0105` 提供 DEB 回流；
- 输出虚线连接 `FV0102`；
- 在控制块旁标注 `BTOT/FFE` 和 `B2 trim`。

#### 第二层：乙烯进料

画布左下布置：

```text
新鲜乙烯 → 压缩机 C0101 → PI0103 → FI0103 → TI0103 → R1
```

控制关系：

```text
FI0103 --虚线→ FIC0103 --虚线→ FV0103
```

#### 第三层：R1

R1 放在三股进料汇合点右侧。R1 周围放置：

- `LI0101`：釜内液位；
- `LIC0101`：液位控制器；
- `LV0101`：R1 出口阀；
- `TI0104`：R1 出口温度；
- `PI0104`：R1 出口压力；
- `FI0104`：R1 出口流量。

控制线：

```text
LI0101 → LIC0101 → LV0101
TI0104 → TIC0104 → PIC0107
```

R1 上方或下方画蒸汽发生/移热支路，标注 `PI0107` 和 `PIC0107`。`TIC0104` 的输出是内环设定值，不是直接阀门开度。

#### 第四层：DEB 回流与 R2

R1 出料向右下进入第二个混合点。C2 返回的 DEB 回流线从画布底部或右下方回到该混合点：

```text
DEB 回流入口 → PI0105 → FI0105 → TI0105 ┐
                                             ├→ 混合点 → R2
R1 出料 ------------------------------------┘
```

R2 周围放置：

- `LI0102`、`LIC0102`、`LV0102`；
- R2 出口 `PI0106`、`FI0106`、`TI0106`；
- R2 出口箭头指向 `02 乙苯分离车间/C1`。

#### 现有 01 画板需要修正的细节

当前数据库中的现有画板配置有三个前端显示问题，补画时一并修正：

1. 绑定 `FI0106::flow_rate` 的节点标签误写为 `FI0116`，应改为 `FI0106`；
2. 多个 PI/FI 节点的 `symbol` 当前仍显示为 `TT`，应按前缀显示 PI/FI/TI/LI；
3. 部分节点单位仍是 MPa、m³/s、℃，本 Luyben 画面应统一成 atm、kmol/h、K，或在全项目采用另一套单位后整体换算，不能混用。

### 8.3 02 乙苯分离车间画板布局

02 车间的 `乙苯分离 P&ID` 视图已创建，但画布 config 为空，等待前端补充。

#### 总体布局

- C1 位于画布左侧；
- C2 位于画布右侧；
- R2 出料从左进入 C1；
- C1 塔顶循环苯从顶部返回 01 车间；
- C1 塔底从中下部进入 C2；
- C2 塔顶 EB 产品从右上输出；
- C2 塔底 DEB 从底部回到 01 车间 R2。

#### C1 苯回收塔

主物流：

```text
来自 R2 → FI0201 → C1
C1 塔顶 → 回流罐 → 分成 C1 回流 FI0202 和循环苯 FI0203
C1 塔底 → FI0204 → C2
```

C1 仪表和控制：

```text
PI0201 → PIC0201 → PV0201（冷凝负荷）
TI0201 → TIC0201 → TV0201（再沸器负荷）
LI0201 → LIC0201 → LV0201（塔底出料）
LI0202 → LIC0202 → LV0202（循环苯出料）
FI0201 + FI0202 → FRC0201 → FV0202（回流阀）
```

`TI0201` 应连接到 C1 第 14 级附近，而不是简单放在塔顶或塔底。

#### C2 乙苯精制塔

主物流：

```text
FI0204 → C2
C2 塔顶 → 回流罐 → 分成回流 FI0205 和 EB 产品 FI0206
C2 塔底 → FI0207 → 返回 01 车间 R2
```

C2 仪表和控制：

```text
PI0202 → PIC0202 → PV0202（冷凝负荷）
TI0202 → TIC0202 → TV0202（再沸器负荷）
LI0203 → LIC0203 → LV0203（DEB 回流）
LI0204 → LIC0204 → LV0204（EB 产品）
FI0204 + FI0205 → FRC0202 → FV0205（回流阀）
AI0201 放在 FI0206 后方，显示 EB 产品纯度
```

`TI0202` 应连接到 C2 第 20 级附近。

#### 跨车间回流

顶部循环苯线标注：

```text
FI0203 → 01 车间 FI0101
```

底部 DEB 回流线标注：

```text
FI0207 → 01 车间 FI0105
```

两个车间使用不同 Sensor 表示边界两侧测点，这是教学 P&ID 常见做法，不要求两者数值自动耦合。

### 8.4 画板节点绑定

Sensor 节点绑定使用 Project point_id：

| 仪表类型 | 示例 point_id |
|---|---|
| FI | `FI0201::flow_rate` |
| PI | `PI0201::pressure` |
| TI | `TI0201::temperature` |
| LI | `LI0201::level` |
| AI | `AI0201::eb_mol_fraction` |

Device 节点直接绑定 Device ID，例如 `TV0201`、`LV0203`。

Controller 节点主要用于说明控制关系，可显示 ControlScheme/AutomationRule 名称；如果当前前端没有控制器专用绑定类型，先使用静态文本节点或控制器符号，不必为此修改后端。

## 九、Project 视图现状

### 9.1 01 车间已有视图

- `P&ID`：已有画布，保留并按第八章补充；
- `仪表与设备`：card；
- `趋势图`：timeseries；
- `自动化控制`：control。

### 9.2 02 车间已创建视图

- `乙苯分离 P&ID`：diagram，当前空白；
- `仪表与设备`：card；
- `趋势图`：timeseries；
- `自动化控制`：control。

## 十、建议启用顺序

所有方案当前停用。完成模拟节点和 P&ID 后按以下顺序逐个启用。

### 10.1 数据确认

1. 确认需要使用的 Sensor 已上报；
2. 确认 data_key 与本文一致；
3. 确认 Device 能响应命令并回传 check_code；
4. 在卡片和趋势页检查单位；
5. 不要在没有 PV 时启动回路。

### 10.2 普通控制方案

建议逐个使用“试一下”，确认命令方向后再启动：

1. `FIC0103`；
2. `LIC0101`、`LIC0102`；
3. `TIC0104`；
4. `PIC0201`、`PIC0202`；
5. `LIC0201-0204`；
6. `TIC0201`、`TIC0202`。

### 10.3 组合控制脚本

基础测点和执行器确认后再启动：

1. `FRC0201`；
2. `FRC0202`；
3. `FRC0102 + VPC0101`。

组合脚本启动前先单次执行，观察返回值和设备状态。

## 十一、通过命令完成的创建结果

本次命令使用 `update_or_create` 和数据库事务，重复执行不会重复创建。

| 对象 | 新增 | 更新/复用 |
|---|---:|---:|
| SensorType | 1 | 0 |
| DeviceType | 5 | 0 |
| Sensor | 19 | 19 |
| Device | 15 | 0 |
| ProjectSensorMember | 19 | 19 |
| ProjectDeviceMember | 15 | 0 |
| ProjectView | 4 | 0 |
| ControlScheme | 12 | 0 |
| AutomationRule | 3 | 0 |

校验结果：

- 01 车间可见 Sensor member：22；
- 02 车间可见 Sensor member：16；
- 12 个新 ControlScheme 全部 `idle/disabled`；
- 3 条新 AutomationRule 全部 `idle/not launched`；
- 3 条脚本均通过 Python 语法编译；
- 没有执行“试一下”，没有向新 Device 下发命令；
- 没有改动现有 P&ID config。

### 11.1 查看创建结果

```bash
docker exec iot-backend python manage.py shell -c "from automation.models import ControlScheme,AutomationRule; print(list(ControlScheme.objects.filter(project__code='EB').values_list('name','is_enabled'))); print(list(AutomationRule.objects.filter(project__code='EB').values_list('name','is_launched')))"
```

### 11.2 查看 02 车间成员

```bash
docker exec iot-backend python manage.py shell -c "from projects.models import ProjectSensorMember,ProjectDeviceMember; print(list(ProjectSensorMember.objects.filter(project__code='EB',section__name='乙苯分离车间').values_list('tag','data_key'))); print(list(ProjectDeviceMember.objects.filter(project__code='EB',section__name='乙苯分离车间').values_list('tag',flat=True)))"
```

## 十二、L1 验收标准

### 12.1 数据结构

- 乙苯控制内容位于现有 `EB` Project；
- 只使用 01、02 两个车间；
- 所有仪表均为前缀加四位号码；
- 后两位按物料方向排列；
- 设备和仪表 description 完整；
- 主模型没有乙苯专用字段。

### 12.2 P&ID

- 01 车间两反应器和两条回流关系完整；
- 02 车间 C1/C2、冷凝器、回流罐、再沸器完整；
- 循环苯和 DEB 跨车间回流方向正确；
- 物流实线和控制虚线可区分；
- 所有 Sensor 绑定正确 point_id；
- 所有 Device 绑定正确 Device ID；
- `FI0116` 标签错误已修正为 `FI0106`；
- 仪表 symbol 和单位已统一。

### 12.3 控制

- P-only 回路使用 PI 且 Ki=0；
- 论文三个温度回路参数已填写；
- 总苯比值和 VPC 脚本资源正确；
- C1/C2 R/F 脚本资源正确；
- 单次执行时输入缺失会返回 False；
- 用户确认后才启动轮询。

### 12.4 不属于验收范围

- 不验证执行器是否改变 Sensor 波形；
- 不验证 EB/DEB 物料衡算；
- 不验证论文图 9-15；
- 不检测脚本和 ControlScheme 的设备争用；
- 不提供生产安全保证。

## 十三、注意事项

1. 当前 FI SensorType 的字段是 `flow_rate`，不是初稿里的 `flow`；脚本和画板绑定必须使用 `flow_rate`。
2. `PIC0107` 在数据库中是 Device，表示蒸汽压力内环设定值接口；P&ID 上仍按控制器显示。
3. `PIC0201`、`PIC0202` 和 `FIC0103` 的参数是教学初值，因为论文没有给出完整整定结果。
4. 温度控制器参数已从论文分钟制积分时间换算为当前控制器的秒制 Ki。
5. 所有命令需要模拟 Device 回传 check_code；没有模拟节点时请保持控制停用。
6. 当前系统实际数据库是 Docker MySQL，后续检查必须继续使用 `docker exec iot-backend`，不要查看本地 SQLite。
7. 前端源码修改后必须重新构建 frontend 镜像才能上线。

## 十四、虚拟传感器与设备

### 14.1 模拟文件

已创建：

```text
simulation/manifests/luyben_eb.yaml
```

清单包含：

- 38 个 `generic_sensor`；
- 15 个 `generic_device`；
- 与运行库 Sensor/Device 完全一致的 ID；
- Luyben 稳态值附近的小幅独立正弦波；
- 5 秒工艺采样周期、10 秒组分采样周期、30 秒状态周期。

### 14.2 模拟边界

传感器信号彼此独立：

- `FV0102` 开度变化不会改变 `FI0102`；
- `TV0201` 负荷变化不会改变 `TI0201`；
- `PV0202` 负荷变化不会改变 `PI0202`；
- 设备命令只更新设备自己的 `opening`、`duty` 或 `setpoint` 状态。

这与本方案的 L1 教学范围一致。它用于验证数据上报、实时画面、趋势、控制计算、命令下发和 check_code 确认，不用于验证工艺动态。

### 14.3 关键模拟值

| 点位 | 波形中心/范围 |
|---|---|
| `FI0101` | 约 969.4 kmol/h |
| `FI0102`、`FI0103` | 约 630.6 kmol/h |
| `FI0105`、`FI0207` | 约 251.2 kmol/h |
| `TI0104` | 432.7-434.7 K |
| `PI0104` | 19.8-20.2 atm |
| `TI0201` | 364.8-366.8 K |
| `TI0202` | 393.5-395.5 K |
| `PI0201` | 0.295-0.305 atm |
| `PI0202` | 0.098-0.102 atm |
| `AI0201` | 0.9985-0.9995 EB mol fraction |

执行器初始值：

- 阀门开度：50%；
- `PIC0107` setpoint：414.9；
- `TV0201` duty：1.99×10⁶ cal/s；
- `TV0202` duty：2.42×10⁶ cal/s；
- 冷凝负荷执行器：50% 教学值。

### 14.4 generic_device 命令兼容

`generic_device` 已补充与平台 DeviceType.commands 一致的命令：

```text
set_opening {value|val}  → opening
set_duty {value|val}     → duty
set_setpoint {value|val} → setpoint
```

命令值会按 manifest 的 min/max 限幅，并立即发布带原 check_code 的状态。原有 `set_state` 仍然保留。

### 14.5 校验与启动

只校验，不连接 broker：

```bash
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python simulation/run.py --check -m luyben_eb
```

启动全部 53 个节点：

```bash
/Users/xhr_mac/miniconda3/envs/iot_platform_env/bin/python simulation/run.py -m luyben_eb
```

停止使用 `Ctrl-C`。

不要把 `luyben_eb` 和 `test-sample` 同时启动；两者都使用 `FI0101/PI0101/TI0101/LI0101`，会产生 MQTT client_id 和主题冲突。

### 14.6 已完成校验

- manifest schema 校验：53 个节点全部通过；
- 构造校验：成功实例化 38 个 Sensor 节点和 15 个 Device 节点；
- `generic_device.py` 编译通过；
- `set_opening` 120 被限幅为 100；
- `set_duty`、`set_setpoint` 状态更新正确；
- 三种命令均原样回传 check_code。

## 十五、参考资料

1. Luyben, W. L. “Design and Control of the Ethyl Benzene Process.” *AIChE Journal*, 57(3), 655-670, 2011. DOI: 10.1002/aic.12289。
2. 论文图 1：乙苯流程；图 8：原始 plantwide control structure；表 6：R/F；表 7：温度回路和 VPC 参数；图 11：VPC 结构。
3. `docs/backend/backend_user_guide/project_guide.md`。
4. `docs/backend/backend_user_guide/AutomationRules_guide.md`。
5. `docs/backend/backend_design/project_design.md`。
