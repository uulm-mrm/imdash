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

    def render(self):

        viz.autogui(self.data)


class FileSystemConnector(ConnectorBase):

    def __init__(self):

        super().__init__("/files")

        self.show_hidden = False

    def cleanup(self):
        pass

    def render(self, views, sources):

        if viz.tree_node("files"):
            self.render_file_tree(views, sources)
            viz.tree_pop()

    def render_file_tree(self, views, sources, path="/"):

        viz.push_id(path)

        fn = os.path.basename(path)
        ext = fn.split(".")[-1].lower()

        if os.path.isdir(path):
            if path != "/":
                node_open = viz.tree_node(fn + "/")
            else:
                node_open = True
            if node_open:
                try:
                    entries = []
                    for p in sorted(os.listdir(path)):
                        if p.startswith(".") and not self.show_hidden:
                            continue
                        tp = os.path.join(path, p)
                        entries.append(tp)
                    for tp in entries:
                        self.render_file_tree(views, sources, tp)
                except PermissionError:
                    viz.text("permission denied", color=(1.0, 0.0, 0.0))
                if path != "/":
                    viz.tree_pop()
        else:
            source_path = self.prefix + path
            tree_open = viz.tree_node(fn)

            close_popup = False

            if viz.begin_popup_context_item():
                if viz.menu_item("Select"):
                    sources.select(source_path)
                    close_popup = True
                viz.end_popup()

            if close_popup:
                viz.close_current_popup()

            if tree_open:
                source = sources[source_path]
                if source is not None:
                    source.render()
                viz.tree_pop()

        viz.pop_id()

    def update_sources(self, sources):

        for key, s in sources.items():

            if not key.startswith(self.prefix):
                continue

            reload_required = False
            if s is not None:
                try:
                    if os.path.getmtime(s.file_path) > s.mod_time:
                        reload_required = True
                except (FileNotFoundError, PermissionError):
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

                except (FileNotFoundError, PermissionError):
                    pass
            else:
                s.mod = False
