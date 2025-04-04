import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


class Image2DComp(View2DComponent):

    DISPLAY_NAME = "Image"

    def __init__(self):

        super().__init__()

        self.source = DataSource(default=None, use_expr=True)
        self.flip_horizontally = False
        self.flip_vertically = False
        self.interpolate = True
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.x_scale = 1.0
        self.y_scale = 1.0
        self.tint = ColorEdit()

    def __autogui__(self, name, ctx, **kwargs):

        viz.push_mod_any()
        ctx.render(self.__dict__, name)
        if viz.pop_mod_any():
            self.source.set_mod()

    def render(self, idx, view):

        img = self.source()

        if self.flip_vertically and self.flip_horizontally:
            uv0 = [1.0, 1.0]
            uv1 = [0.0, 0.0]
        elif self.flip_vertically:
            uv0 = [0.0, 1.0]
            uv1 = [1.0, 0.0]
        elif self.flip_horizontally:
            uv0 = [1.0, 0.0]
            uv1 = [0.0, 1.0]
        else:
            uv0 = [0.0, 0.0]
            uv1 = [1.0, 1.0]

        skip_upload = not self.source.mod()

        flags = viz.PlotImageFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT

        item_id = self.label + f"###{self.uuid}"

        viz.plot_dummy(item_id)
        viz.plot_image(
            item_id,
            img,
            self.x_offset,
            self.y_offset,
            img.shape[1] * self.x_scale,
            img.shape[0] * self.y_scale,
            tint=self.tint(),
            uv0=uv0,
            uv1=uv1,
            skip_upload=skip_upload,
            interpolate=self.interpolate,
            flags=flags)
