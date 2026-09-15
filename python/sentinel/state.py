from dataclasses import dataclass
import math


@dataclass
class StateMachine:
    warning: float = 0.5
    fault: float = 0.8
    recovery: float = 0.3
    persistence: int = 3
    recovery_windows: int = 5
    state: str = "UNKNOWN"
    high: int = 0
    low: int = 0

    def __post_init__(self):
        if not 0 <= self.recovery < self.warning < self.fault <= 1:
            raise ValueError("thresholds must satisfy recovery < warning < fault")
        if self.persistence < 1 or self.recovery_windows < 1:
            raise ValueError("persistence must be positive")

    def update(self, score):
        if score is None or not math.isfinite(score) or not 0 <= score <= 1:
            self.state, self.high, self.low = "UNKNOWN", 0, 0
            return self.state
        self.high = self.high + 1 if score >= self.fault else 0
        self.low = self.low + 1 if score <= self.recovery else 0
        if self.high >= self.persistence:
            self.state = "FAULT"
        elif self.state == "FAULT":
            if self.low >= self.recovery_windows:
                self.state = "NORMAL"
        elif score >= self.warning:
            self.state = "WARNING"
        elif self.low >= self.recovery_windows:
            self.state = "NORMAL"
        return self.state
