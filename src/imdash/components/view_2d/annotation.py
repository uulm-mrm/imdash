import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Annotation2DComp(View2DComponent):

    DISPLAY_NAME = "Annotation"

    def __init__(self):

        super().__init__()

        self.text = DataSource(default="", use_expr=False)

        self.x = DataSource(default=0.0, use_expr=False)
        self.y = DataSource(default=0.0, use_expr=False)

        self.offset_x = 0.0
        self.offset_y = 0.0
        self.clamp = False

        self.color = ColorEdit(default=np.array([1.0, 1.0, 0.0]))

    def render(self, idx, view):

        x = float(self.x())
        y = float(self.y())
        text = str(self.text())

        viz.plot_annotation(x,
                            y,
                            text,
                            self.color(),
                            (self.offset_x, self.offset_y),
                            self.clamp)
