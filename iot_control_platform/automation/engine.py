"""
自动化规则引擎
根据 sample_file 设计：脚本通过 from engine import sensors, devices 获取依赖
支持类形式控制器（__init__ 相当于 setup，loop() 相当于 Arduino loop()）

安全策略：
- 白名单 import：仅允许导入 engine / automation.head_files 下的模块
- 禁用危险内置函数（open, eval, exec, compile, __import__ 原始版, globals, locals 等）
- 脚本在受限命名空间中执行
"""
import logging
import types
from typing import Optional

import builtins as _bi

logger = logging.getLogger(__name__)

# 允许脚本 import 的模块白名单（前缀匹配）
# 注意：仅添加可信模块，危险模块（如 os, subprocess, socket, sys 等）禁止引入
# 基础白名单 + settings 中的可配置白名单
_BASE_IMPORT_WHITELIST = ('engine', 'automation.head_files')

def _get_import_whitelist():
    """动态获取导入白名单，结合基础白名单和 settings 配置"""
    from django.conf import settings
    allowed = list(_BASE_IMPORT_WHITELIST)
    extra = getattr(settings, 'AUTOMATION_ALLOWED_IMPORTS', [])
    if extra:
        allowed.extend(extra)
    return tuple(allowed)

# 禁用的内置函数：禁止文件/进程/动态代码操作
_BLOCKED_BUILTINS = frozenset({
    'open', 'eval', 'exec', 'compile',
    '__import__', 'globals', 'locals',
    'breakpoint', 'input',
})


def _make_safe_builtins(custom_import):
    """构建安全内置函数字典，移除危险函数，替换 __import__"""
    safe = dict(vars(_bi))
    for name in _BLOCKED_BUILTINS:
        safe.pop(name, None)
    safe['__import__'] = custom_import
    return safe


def _make_custom_import(engine_module, real_import):
    """创建自定义 import：仅白名单模块可以通过，其余一律拒绝"""
    def _custom_import(name, *args, **kwargs):
        if name == 'engine':
            return engine_module
        # 动态获取白名单前缀匹配
        whitelist = _get_import_whitelist()
        if any(name == prefix or name.startswith(prefix + '.') for prefix in whitelist):
            return real_import(name, *args, **kwargs)
        raise ImportError(
            f"自动化脚本不允许导入模块 '{name}'，"
            f"仅允许: {', '.join(whitelist)}"
        )
    return _custom_import


def execute_rule(rule) -> bool:
    """
    执行单条自动化规则。
    注入 engine 模块（含 sensors、devices），查找带 loop() 的控制器类并执行一次 loop()。
    在受限沙箱中运行，禁用文件/进程/动态代码操作。
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

    _real_import = _bi.__import__
    custom_import = _make_custom_import(engine, _real_import)
    safe_builtins = _make_safe_builtins(custom_import)

    namespace = {
        '__builtins__': safe_builtins,
        'engine': engine,
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

    except ImportError as e:
        logger.error("自动化规则 [%s] 尝试导入受限模块: %s", rule.name, e)
        return False
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
