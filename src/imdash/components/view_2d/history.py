import time
import queue
import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class History2DComp(View2DComponent):

    DISPLAY_NAME = "History"

    def __init__(self):

        super().__init__()

        self.x_source = DataSource()
        self.y_source = DataSource()
        self.format = "-"
        self.line_weight = 1.0
        self.marker_size = 3.0

        self.color = ColorEdit(default=np.array([1.0, 1.0, 0.0]))

        self.history_length = 1000.0
        self.history_step = 0.01
        self.history = queue.deque()

        self.paused = False

    def __savestate__(self):

        d = self.__dict__.copy()
        del d["history"]

        return d

    def plot_history(self, idx):
        """
        This is a separate function so it can be overridden by base classes.
        """

        xs = [x for x, y in self.history]
        ys = [float(y) for x, y in self.history]

        viz.plot(xs,
                 ys,
                 fmt=self.format,
                 label=f"{self.label}{'' if not self.paused else ' [PAUSED]'}###{idx}",
                 line_weight=self.line_weight,
                 marker_size=self.marker_size,
                 color=self.color())

    def render(self, idx, view):

        for ke in viz.get_key_events():
            if viz.is_window_hovered():
                if ke.action == viz.PRESS and ke.key == viz.KEY_P:
                    self.paused = not self.paused
                if ke.action == viz.PRESS and ke.key == viz.KEY_C:
                    self.history = queue.deque()
            else:
                if (ke.action == viz.PRESS
                        and ke.key == viz.KEY_P
                        and ke.mod == viz.MOD_CONTROL):
                    self.paused = not self.paused

        y_data = self.y_source()

        if self.x_source.path == "":
            if len(self.history) == 0:
                x_data = 0
            else:
                x_data = self.history[-1][0] + 1
        else:
            x_data = float(self.x_source())

        if self.y_source.mod() and not self.paused:
            if len(self.history) == 0:
                self.history.append((x_data, y_data))
            elif x_data - self.history[-1][0] > self.history_step:
                self.history.append((x_data, y_data))
            elif self.history[-1][0] > x_data:
                self.history.clear()

            while len(self.history) > 0 and x_data - self.history[0][0] > self.history_length:
                self.history.popleft()

        if len(self.history) > 0:
            self.plot_history(idx)
