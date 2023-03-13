import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Bars2DComp(View2DComponent):

    DISPLAY_NAME = "Bars"

    def __init__(self):

        super().__init__()

        self.x_source = DataSource(default=0.0)
        self.y_source = DataSource(default=0.0)

        self.bar_size = 1.0
        self.horizontal = False

        self.color = ColorEdit(default=np.array([1.0, 1.0, 0.0]))

    def render(self, idx, view):

        # get y data first

        y_data = self.y_source()
        if not hasattr(y_data, "__len__"):
            y_data = [float(y_data)]

        # then get x data
        if self.x_source.path != "":
            x_data = self.x_source()
        else:
            x_data = np.arange(len(y_data))
        if not hasattr(x_data, "__len__"):
            x_data = [float(x_data)]

        flags = viz.PlotBarsFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT
        if self.horizontal:
            flags |= viz.PlotBarsFlags.HORIZONTAL

        viz.plot_bars(x_data,
                      y_data,
                      label=f"{self.label}###{idx}",
                      color=self.color(),
                      bar_size=self.bar_size,
                      flags=flags)
