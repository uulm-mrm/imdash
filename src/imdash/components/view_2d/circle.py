import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Circle2DComp(View2DComponent):

    DISPLAY_NAME = "Shapes/Circle"

    def __init__(self):

        super().__init__()

        ppp = viz.get_plot_popup_point()

        self.x = DataSource(ppp[0], False)
        self.y = DataSource(ppp[1], False)
        self.radius = DataSource(1.0, False)

        self.color = ColorEdit()
        self.line_width = DataSource(1.0, False)
        self.segments = 36

    def render(self, idx, view):

        pos = (self.x(), self.y())
        radius = self.radius()
        line_width = self.line_width()

        viz.plot_circle(
                pos,
                radius,
                f"{self.label}###{idx}",
                self.color(),
                self.segments,
                line_width)
