import time


class SimpleTimer(object):

    def __init__(self):
        self.reset()

    def now(self):
        return time.time()

    def elapsed(self):
        return self.now() - self.t0

    def reset(self):
        self.t0 = self.now()


class FPSCounter(object):

    def __init__(self):
        self.averageComputer = MovingAverageComputer()
        self.lastUpdateTime = self.averageComputer.timer.now()

    def update(self):
        currentTime = self.averageComputer.timer.now()
        dt = currentTime - self.lastUpdateTime
        if dt > 0:
            self.averageComputer.update(1.0 / dt)
        self.lastUpdateTime = currentTime

    def getAverageFPS(self):
        return self.averageComputer.getAverage()


class AverageComputer(object):

    def __init__(self):
        self.timer = SimpleTimer()
        self.quantity = 0.0

    def update(self, quantitySinceLastUpdate):
        self.quantity += quantitySinceLastUpdate

    def getAverage(self):
        return self.quantity / self.timer.elapsed()

    def reset(self):
        self.quantity = 0.0
        self.timer.reset()


class MovingAverageComputer(object):

    def __init__(self):
        self.timer = SimpleTimer()
        self.quantity = 0.0
        self.alpha = 0.9

    def update(self, quantitySinceLastUpdate):
        dt = self.timer.elapsed()
        if dt > 0:
            self.quantity = self.alpha * self.quantity + (1.0 - self.alpha) * quantitySinceLastUpdate
            self.timer.reset()

    def getAverage(self):
        return self.quantity

    def reset(self):
        self.quantity = 0.0
        self.timer.reset()

