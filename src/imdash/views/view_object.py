import os
import uuid
import copy
import traceback

import imviz as viz
import objtoolbox as otb

from imdash.utils import (
        DataSource,
        ViewBase
    )

from pydoc import locate


class ImdashAutoguiContext(viz.AutoguiContext):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.func_cache = {}

        self.file_path_needed = False
        self.file_path_id = None
        self.file_path = None

    def request_file_path(self, fp_id):

        self.file_path_needed = True
        self.file_path_id = viz.get_id(fp_id)

    def get_file_path(self, fp_id):

        if self.file_path_id != viz.get_id(fp_id):
            return None

        if self.file_path is not None:
            self.file_path_id = None
            res = self.file_path
            self.file_path = None
            return res

        return None

    def render(self, obj, name=""):

        if hasattr(obj, "__renderer__") and not self.ignore_custom:
            viz.push_mod_any()
            try:
                render_func = locate(obj.__renderer__)
                res = render_func(obj, name, ctx=self, **self.params)
            except Exception as e:
                traceback.print_exc()
                return super().render(obj, name)
            if viz.pop_mod_any():
                if self.path_of_mod_item == []:
                    self.path_of_mod_item = copy.deepcopy(self.path)
            return res

        return super().render(obj, name)


class ViewObject(ViewBase):

    def __init__(self):

        super().__init__()

        self.title = "View Object"
        self.source = DataSource()

        self.readwrite = False

        self.file_path_needed = False
        self.file_action = None
        self.file_path = os.path.realpath(os.path.expanduser("~"))
        self.file_path_id = None

    def __savestate__(self):

        s = self.__dict__.copy()
        del s["file_path_needed"]
        del s["file_action"]
        del s["file_path"]

        return s

    def import_object(self, path, obj):

        otb.load(obj, path)

    def export_object(self, path, obj):

        otb.save(obj, path)

    def store_file_path_id(self, fp_id):

        self.file_path_id = fp_id

    def context_menu_hook(self, obj, name, ctx):

        if viz.begin_popup_context_item(name):
            if viz.menu_item("Import"):
                self.file_path_needed = True
                self.file_action = lambda p: self.import_object(p, obj)
            if viz.menu_item("Export"):
                self.file_path_needed = True
                self.file_action = lambda p: self.export_object(p, obj)
            viz.end_popup()

    def render(self, sources):

        if not self.show:
            return

        src_rw = self.source.readwrite()
        rw = src_rw and self.readwrite

        title = f"{self.title}" + ("" if rw else "  -  [readonly]")

        window_open = viz.begin_window(f"{title}###{self.uuid}")
        if viz.begin_popup_context_item():
            if viz.begin_menu("Edit"):
                self.title = viz.input("title", self.title)
                viz.autogui(self.source, "source", sources=sources)
                viz.begin_disabled(not src_rw)
                self.readwrite = viz.checkbox("readwrite", rw and self.readwrite)
                viz.end_disabled()
                viz.end_menu()
            if viz.menu_item("Destory"):
                self.destroyed = True
            viz.end_popup()
        self.show = viz.get_window_open()

        agc = ImdashAutoguiContext()
        agc.post_header_hooks.append(self.context_menu_hook)
        if self.file_path_id is not None:
            agc.file_path_id = self.file_path_id
            agc.file_path = self.file_path
            self.file_path_id = None

        if window_open:
            try:
                if rw:
                    s = self.source.get_used_source()
                else:
                    s = self.source()
                try:
                    agc.render(s)
                except IndexError:
                    agc.render(s, "value")
            except Exception as e:
                viz.text(traceback.format_exc())

        viz.end_window()

        popup_id = f"Select path###sel_path_{self.uuid}"
        if self.file_path_needed:
            viz.open_popup(popup_id)
            self.file_path_needed = False

        if agc.file_path_needed:
            viz.open_popup(popup_id)
            agc.file_path_needed = False
            self.file_action = lambda _: self.store_file_path_id(agc.file_path_id)

        self.file_path = viz.file_dialog_popup(popup_id, self.file_path)
        if viz.mod():
            self.file_action(self.file_path)
            self.file_action = None
