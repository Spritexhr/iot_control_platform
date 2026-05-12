"""
仿真数据波形生成器

提供可参数化的数据源，供各虚拟传感器读数使用。每个节点在 config.yaml 里
为每个上报字段指定一种波形，例如：

    waveforms:
      temperature: {type: sine, min: 18, max: 28, period: 3600, jitter: 0.3}
      humidity:    {type: random_walk, start: 55, step: 1.5, bounds: [40, 70]}

通过 build_waveform(cfg) 把 dict 装配成具体实例，调用 .sample() 取下一个值。
"""
import math
import random
import time
from typing import Tuple


class Waveform:
    def sample(self) -> float:
        raise NotImplementedError


class SineWave(Waveform):
    """
    正弦波，适合昼夜温度、潮汐等周期性信号。

    Args:
        min: 波形最小值
        max: 波形最大值
        period: 周期（秒）
        jitter: 在采样值上叠加的均匀噪声幅度（±jitter），默认 0
        phase: 初始相位偏移（秒），默认 0；多个同型节点可错开避免完全同步
    """
    def __init__(self, min: float, max: float, period: float,
                 jitter: float = 0.0, phase: float = 0.0):
        self.min = float(min)
        self.max = float(max)
        self.period = float(period)
        self.jitter = float(jitter)
        self._t0 = time.time() - float(phase)

    def sample(self) -> float:
        amplitude = (self.max - self.min) / 2.0
        center = (self.max + self.min) / 2.0
        elapsed = time.time() - self._t0
        v = center + amplitude * math.sin(2.0 * math.pi * elapsed / self.period)
        if self.jitter:
            v += random.uniform(-self.jitter, self.jitter)
        return v


class RandomWalk(Waveform):
    """
    随机游走，适合湿度、电池电量这种慢变量。

    Args:
        start: 初始值
        step: 每次采样的最大步长（实际步长在 ±step 间均匀分布）
        bounds: [下界, 上界]，越界后会被夹回
    """
    def __init__(self, start: float, step: float, bounds: Tuple[float, float]):
        self.value = float(start)
        self.step = float(step)
        lo, hi = bounds
        self.lo = float(lo)
        self.hi = float(hi)

    def sample(self) -> float:
        self.value += random.uniform(-self.step, self.step)
        if self.value < self.lo:
            self.value = self.lo
        elif self.value > self.hi:
            self.value = self.hi
        return self.value


class UniformRandom(Waveform):
    """[min, max] 区间内均匀分布的独立采样，无记忆。"""
    def __init__(self, min: float, max: float):
        self.min = float(min)
        self.max = float(max)

    def sample(self) -> float:
        return random.uniform(self.min, self.max)


class Constant(Waveform):
    """恒定值，适合开关类（0/1）或固定基线。"""
    def __init__(self, value: float):
        self.value = float(value)

    def sample(self) -> float:
        return self.value


WAVEFORM_REGISTRY = {
    "sine": SineWave,
    "random_walk": RandomWalk,
    "uniform": UniformRandom,
    "constant": Constant,
}


def build_waveform(cfg: dict) -> Waveform:
    """
    把配置字典装配成 Waveform 实例。

    cfg 形如 {"type": "sine", "min": 18, "max": 28, "period": 3600}
    或简写 {"type": "constant", "value": 42}
    """
    if not isinstance(cfg, dict) or "type" not in cfg:
        raise ValueError(f"波形配置必须是含 'type' 字段的字典，收到: {cfg!r}")
    params = {k: v for k, v in cfg.items() if k != "type"}
    wf_type = cfg["type"]
    cls = WAVEFORM_REGISTRY.get(wf_type)
    if cls is None:
        raise ValueError(
            f"未知波形类型 '{wf_type}'，可选: {list(WAVEFORM_REGISTRY.keys())}"
        )
    return cls(**params)


def build_waveform_map(cfg: dict) -> dict:
    """
    把 {字段名: 波形配置} 批量装配成 {字段名: Waveform 实例}
    """
    return {field: build_waveform(c) for field, c in (cfg or {}).items()}
