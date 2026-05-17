"""
公用服务层包。

只作命名空间使用，**不在此做任何顶层 import**——否则当 Django apps
populate 期间 import 任何 services.* 子包时，会拉链触发 models 的
import，引发 AppRegistryNotReady。

请按需 `from services.mqtt_service import mqtt_service` 等子模块路径导入。
"""
