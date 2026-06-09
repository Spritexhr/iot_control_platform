# simulation —— 虚拟传感器与设备仿真

复刻 `hardware/wemos-d1/` 下各 `.ino` 固件的 MQTT 行为，用 Python 模拟一台台"软件版的硬件"，跑在 Mac/Linux 上而不是 ESP8266 上。与 Django 后端完全解耦，仿真器只是一组 MQTT 客户端。

**完整文档已统一收录到 `docs/simulation/`：**

- [仿真模块使用说明](../docs/simulation/simulation_guide.md) —— 目录结构、环境、配置、启动方式、节点目录、波形、与后端对接、添加新节点
- [端到端验证教程](../docs/simulation/testing_guide.md) —— L1 日志 / L2 抓包 / L3 入库 / L4 批量启动

## 快速上手

```bash
conda create -n simulation_env python=3.11 -y && conda activate simulation_env
pip install -r simulation/requirements.txt
cp simulation/config.yaml.example simulation/config.yaml   # 改 broker.host

python simulation/run.py                       # 加载 manifests/default.yaml
python simulation/run.py -m st_plant           # 苯乙烯装置清单
```
