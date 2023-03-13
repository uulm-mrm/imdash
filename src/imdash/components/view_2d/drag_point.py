import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class DragPoint2DComp(View2DComponent):

    DISPLAY_NAME = "Interactive/Drag point"

    def __init__(self):

        super().__init__()

        pp = viz.get_plot_popup_point()

        self.x = DataSource(default=pp[0], use_expr=False)
        self.y = DataSource(default=pp[1], use_expr=False)

        self.color = ColorEdit()
        self.radius = 5.0

    def render(self, idx, view):

        x, y = self.x(), self.y()

        viz.plot_dummy(f"{self.label}###{idx}", self.color())

        flags = viz.PlotDragToolFlags.DELAYED
        if self.no_fit:
            flags |= viz.PlotDragToolFlags.NO_FIT

        x, y = viz.drag_point(
                "###{idx}dragpoint",
                (x, y),
                self.color(),
                self.radius,
                flags)

        if viz.mod():
            self.x.set(x)
            self.y.set(y)
