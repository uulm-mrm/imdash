import os
import time
import imviz as viz

from imdash.utils import ViewBase, DataSource
from PIL import Image


class ImageSaverView(ViewBase):

    def __init__(self):

        super().__init__()

        self.title = "Image Saver"
        self.image_source = DataSource()

        self.save_path = os.path.abspath(os.path.expanduser("~/"))

        self.error_msg = None

        self.save_every_second = False
        self.last_save_time = time.time()

    def __savestate__(self):

        d = self.__dict__.copy()
        del d["error_msg"]
        del d["last_save_time"]
        del d["save_every_second"]

        return d

    def __autogui__(self, name, ctx, **kwargs):

        self.title = ctx.render(self.title, "title")

    def save_image(self, img):

        try:
            if os.path.isdir(self.save_path):
                pil_img = Image.fromarray(img)
                stamp = str(int(time.time() * 10**9))
                file_path = os.path.join(self.save_path, stamp) +  ".png"
                pil_img.save(file_path)
            else:
                pil_img = Image.fromarray(img)
                ext = os.path.splitext(self.save_path)[-1]
                if ext != ".png":
                    pil_img = pil_img.convert("RGB")
                pil_img.save(self.save_path)
            self.error_msg = None
        except Exception as e:
            self.error_msg = str(e)

    def render(self, sources):

        if not self.show:
            return

        window_open = viz.begin_window(f"{self.title}###{self.uuid}")
        self.show = viz.get_window_open()

        if viz.begin_popup_context_item():
            if viz.begin_menu("Edit"):
                viz.autogui(self, "", sources=sources)
                viz.end_menu()
            if viz.menu_item("Delete"):
                self.destroyed = True
            viz.end_popup()

        try:
            img = self.image_source()
        except Exception:
            img = None

        if window_open:
            viz.autogui(self.image_source, "image", sources=sources)

            viz.separator()

            self.save_path = viz.file_dialog_popup("Select path", self.save_path)
            if viz.button("..."):
                viz.open_popup("Select path")
            viz.same_line()
            self.save_path = viz.autogui(self.save_path, "path")

            if viz.button("Save image"):
                self.save_image(img)
            viz.same_line()

            self.save_every_second = viz.checkbox("Save every 1s", self.save_every_second)
            if self.save_every_second:
                now = time.time()
                if now - self.last_save_time > 1.0:
                    self.last_save_time = now
                    self.save_image(img)

            if self.error_msg is not None:
                viz.text(self.error_msg, "red")

            viz.separator()
            if viz.begin_plot(f"{self.title}###{self.uuid}",
                              flags=viz.PlotFlags.EQUAL 
                                      | viz.PlotFlags.NO_TITLE
                                      | viz.PlotFlags.NO_LEGEND
                                      | viz.PlotFlags.NONE):
                viz.setup_axes("width in px", "height in px")
                if img is not None:
                    viz.plot_image("image", img)
            viz.end_plot()
        viz.end_window()
