import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Rectangle2DComp(View2DComponent):

    DISPLAY_NAME = "Shapes/Rectangle"

    def __init__(self):

        super().__init__()

        ppp = viz.get_plot_popup_point()

        self.x = DataSource(ppp[0], False)
        self.y = DataSource(ppp[1], False)
        self.size_x = DataSource(1.0, False)
        self.size_y = DataSource(1.0, False)
        self.rotation = DataSource(0.0, False)
        self.origin_x = DataSource(0.5, False)
        self.origin_y = DataSource(0.5, False)

        self.color = ColorEdit()
        self.line_width = DataSource(1.0, False)

    def render(self, idx, view):

        pos = (float(self.x()), float(self.y()))
        size = (float(self.size_x()), float(self.size_y()))
        rotation = float(self.rotation())
        origin = (float(self.origin_x()), float(self.origin_y()))
        line_width = float(self.line_width())

        viz.plot_rect(
                pos,
                size,
                f"{self.label}###{idx}",
                self.color(),
                origin,
                rotation,
                line_width)
