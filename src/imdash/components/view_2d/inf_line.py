import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class InfLine2DComp(View2DComponent):

    DISPLAY_NAME = "Infinite line"

    def __init__(self):

        super().__init__()

        self.pos = DataSource(
                default=viz.get_plot_popup_point()[1],
                use_expr=False)

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
                self.pos.alt_val = viz.get_plot_mouse_pos()[1]
            else:
                self.pos.alt_val = viz.get_plot_mouse_pos()[0]
            self.prev_orientation = self.orienation.index

        return self

    def render(self, idx, view):

        flags = viz.PlotItemFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT

        if self.orienation.index == 0:
            viz.plot_hlines(f"{self.label}###{idx}",
                            [float(self.pos())],
                            color=self.color(),
                            width=self.width,
                            flags=flags)
        else:
            viz.plot_vlines(f"{self.label}###{idx}",
                            [float(self.pos())],
                            color=self.color(),
                            width=self.width,
                            flags=flags)
