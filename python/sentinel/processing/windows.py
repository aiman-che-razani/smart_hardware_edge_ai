from collections import deque


class Windows:
    def __init__(self, size=800, overlap=0.5):
        if size < 8 or not 0 <= overlap < 1:
            raise ValueError("invalid window configuration")
        self.size = size
        self.step = max(1, round(size * (1 - overlap)))
        self.records = deque(maxlen=size)
        self.since = 0
        self.ready = False

    def clear(self):
        self.records.clear()
        self.since = 0
        self.ready = False

    def add(self, record, discontinuity=False):
        if discontinuity:
            self.clear()
        self.records.append(record)
        self.since += 1
        if len(self.records) == self.size and (not self.ready or self.since >= self.step):
            self.ready = True
            self.since = 0
            return list(self.records)
        return None
