import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource


class Hotkey2DComp(View2DComponent):

    DISPLAY_NAME = "Interactive/Hot key"

    def __init__(self):

        super().__init__()

        self.listen_globally = False
        self.key = DataSource(default="a", use_expr=False)
        self.value = DataSource(default=None, use_expr=True)
        self.target = DataSource(default=None, use_expr=True)

    def render(self, idx, view):

        self.target()

        if viz.is_window_hovered() or self.listen_globally:
            for ke in viz.get_key_events():
                key_name = str(self.key()).upper()
                if (ke.action == viz.PRESS
                        and ke.key == getattr(viz, f"KEY_{key_name}")):
                    val = self.value()
                    self.target.set(val)
