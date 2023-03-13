import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class DragLine2DComp(View2DComponent):

    DISPLAY_NAME = "Interactive/Drag line"

    def __init__(self):

        super().__init__()

        self.pos = viz.get_plot_popup_point()[1]

        self.orienation = viz.Selection(["horizontal", "vertical"])
        self.prev_orientation = self.orienation.index

        self.color = ColorEdit()

        self.width = 1.0

    def __autogui__(self, name, ctx, **kwargs):

        s = self.__dict__.copy()
        del s["prev_orientation"]

        self.__dict__.update(ctx.render(s, name))

        if self.prev_orientation != self.orienation.index:
            if self.orienation.index == 0:
                self.pos = viz.get_plot_mouse_pos()[1]
            else:
                self.pos = viz.get_plot_mouse_pos()[0]
            self.prev_orientation = self.orienation.index

        return self

    def render(self, idx, view):

        flags = viz.PlotDragToolFlags.DELAYED
        if self.no_fit:
            flags |= viz.PlotDragToolFlags.NO_FIT

        viz.plot_dummy(f"{self.label}###{idx}", self.color())

        if self.orienation.index == 0:
            self.pos = viz.drag_hline(
                    "###{idx}dragline",
                    self.pos,
                    self.color(),
                    self.width,
                    flags=flags)
        else:
            self.pos = viz.drag_vline(
                    "###{idx}dragline",
                    self.pos,
                    self.color(),
                    self.width,
                    flags=flags)
