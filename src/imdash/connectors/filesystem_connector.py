import os
import json
import imviz as viz
import numpy as np

import objtoolbox as otb
from PIL import Image

from imdash.connectors.connector_base import ConnectorBase


class FileSource:

    def __init__(self):

        self.file_path = None

        self.data = None

        self.mod_time = 0.0
        self.mod = True

    def __autogui__(self, name, ctx, **kwargs):

        return ctx.render(self.data, name)


class FileSystemConnector(ConnectorBase):

    def __init__(self):

        super().__init__("/files")

        self.show_hidden = False
        self.selected_path = os.path.abspath(os.path.expanduser("~"))

    def cleanup(self):
        pass

    def render(self, views, sources):

        if viz.button(f"{viz.Icon.FOLDER_OPEN}  Select file"):
            viz.open_popup("select_file_source_dialog")

        self.selected_path = viz.file_dialog_popup(
                "select_file_source_dialog", self.selected_path)
        if viz.mod():
            sources.select(self.prefix + self.selected_path)
            viz.close_current_popup()

    def update_sources(self, sources):

        for key, s in sources.items():

            if not key.startswith(self.prefix):
                continue

            reload_required = False
            if s is not None:
                try:
                    if os.path.getmtime(s.file_path) > s.mod_time:
                        reload_required = True
                except:
                    pass

            if s is None or reload_required:

                file_path = key.replace(self.prefix, "")

                try:
                    s = FileSource()
                    s.file_path = file_path
                    s.mod_time = os.path.getmtime(file_path)

                    ext = s.file_path.split(".")[-1].lower()
                    if ext in ["jpg", "jpeg", "png", "bmp", "tiff"]:
                        with Image.open(s.file_path) as img:
                            s.data = np.asarray(img)
                    elif ext == "csv":
                        s.data = np.genfromtxt(s.file_path, delimiter=",")
                    elif ext == "json":
                        dn = os.path.dirname(s.file_path)
                        if (s.file_path.endswith("state.json")
                                and os.path.exists(os.path.join(dn, "extern"))):
                            # most likely otb storage
                            s.data = {}
                            otb.load(s.data, dn)
                        else:
                            with open(s.file_path) as fd:
                                s.data = json.load(fd)
                    else:
                        with open(s.file_path, "r") as fd:
                            s.data = fd.read()

                    sources[key] = s
                except:
                    pass
            else:
                try:
                    s.mod = s.mod_requested
                    s.mod_requested = False
                except AttributeError:
                    s.mod = False
