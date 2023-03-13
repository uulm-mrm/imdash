import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Value2DComp(View2DComponent):

    DISPLAY_NAME = "Value"

    def __init__(self):

        super().__init__()

        self.x_source = DataSource(default=[0.0, 1.0, 2.0])
        self.y_source = DataSource(default=[0.0, 1.0, 2.0])

        self.format = "-"
        self.line_weight = 1.0
        self.marker_size = 3.0

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

        flags = viz.PlotLineFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT

        viz.plot(x_data,
                 y_data,
                 fmt=self.format,
                 label=f"{self.label}###{idx}",
                 line_weight=self.line_weight,
                 marker_size=self.marker_size,
                 color=self.color(),
                 flags=flags)
