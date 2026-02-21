"""
自动化规则引擎
根据 sample_file 设计：脚本通过 from engine import sensors, devices 获取依赖
支持类形式控制器（__init__ 相当于 setup，loop() 相当于 Arduino loop）
"""
import logging
import types
from typing import Optional

logger = logging.getLogger(__name__)

# 使用标准 builtins，仅需在执行时覆盖 __import__
import builtins as _bi


def execute_rule(rule) -> bool:
    """
    执行单条自动化规则。
    注入 engine 模块（含 sensors、devices），查找带 loop() 的控制器类并执行一次 loop()。
    """
    if not rule.script:
        return False

    from automation.head_files.sensors import build_sensors
    from automation.head_files.devices import build_devices

    sensors = build_sensors(rule.device_list)
    devices = build_devices(rule.device_list)

    # 构造 engine 模块，支持 from engine import sensors, devices
    engine = types.ModuleType('engine')
    engine.sensors = sensors
    engine.devices = devices

    # 自定义 __import__：from engine import 时返回我们的 engine 模块
    _real_import = _bi.__import__

    def _custom_import(name, *args, **kwargs):
        if name == 'engine':
            return engine
        return _real_import(name, *args, **kwargs)

    _builtins = dict(vars(_bi))
    _builtins['__import__'] = _custom_import

    namespace = {
        '__builtins__': _builtins,
        'engine': engine,
        # 'sensors': sensors,
        # 'devices': devices,
        'Optional': Optional,
    }

    try:
        script = rule.script.strip()
        exec(compile(script, f'<rule:{rule.name}>', 'exec'), namespace)

        # 查找带 loop() 方法的控制器类，实例化并执行一次 loop()
        controller_cls = _find_controller_class(namespace)
        if controller_cls is None:
            logger.warning("自动化规则 [%s] 未找到带 loop() 的控制器类", rule.name)
            return False

        controller = controller_cls()
        ret = controller.loop()
        return bool(ret) if ret is not None else False

    except Exception as e:
        logger.exception("自动化规则执行异常 [%s]: %s", rule.name, e)
        return False


def _find_controller_class(namespace: dict):
    """从命名空间查找第一个带 loop() 方法的类（非内置）"""
    for name, obj in namespace.items():
        if (isinstance(obj, type)
                and not name.startswith('_')
                and hasattr(obj, 'loop')
                and callable(getattr(obj, 'loop'))):
            return obj
    return None
