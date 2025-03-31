import re
import os
import time
import math
import uuid
import json
import numbers
import hashlib
import traceback
import subprocess

import numpy as np
import imviz as viz

from PIL import Image

import objtoolbox as otb


def speak(text):

    try:
        fd = os.open(os.path.expanduser("~/.speak"),
                     os.O_NONBLOCK | os.O_WRONLY)
        os.write(fd, f"{text}\n".encode("utf8"))
    except:
        pass
    finally:
        os.close(fd)


def begin_context_drag_item(id_str, x, y, button=1, tol=10):

    if viz.is_item_clicked(button):

        mouse_pos = viz.get_plot_mouse_pos()
        mouse_pos = viz.plot_to_pixels(mouse_pos[0], mouse_pos[1])
        mouse_pos = np.array(mouse_pos)

        obj_pos = viz.plot_to_pixels(x, y)
        obj_pos = np.array(obj_pos)

        if np.linalg.norm(mouse_pos - obj_pos) < tol:
            viz.open_popup(id_str)

    return viz.begin_popup(id_str)


class DataSource:

    SRC_PATTERN = re.compile("\{(.+?)\}")
    SRC_GLOBALS = {
            "np": np,
            "time": time,
            "math": math
        }

    FILE_SRC_PATTERN = re.compile("\{/files/(.+?)\}")

    SOURCES = None

    def __init__(self, default=None, use_expr=True, allow_expr=True, path=""):

        self.path = path
        self.new_path = None

        self.use_expr = use_expr
        self.alt_val = default
        self.allow_expr = allow_expr

        if default is None:
            allow_expr = True

    def __savestate__(self):

        s = self.__dict__.copy()

        # convert file paths to relative paths
        path_expr = s["path"]
        for m in re.finditer(DataSource.FILE_SRC_PATTERN, path_expr):
            p = m.group(1)
            path_expr = path_expr.replace(
                    p, os.path.relpath("/" + p, os.getcwd()))
        s["path"] = path_expr

        if self.use_expr:
            del s["alt_val"]

        return s

    def __loadstate__(self, s):

        # convert file paths to absolute paths
        path_expr = s["path"]
        for m in re.finditer(DataSource.FILE_SRC_PATTERN, path_expr):
            p = m.group(1)
            path_expr = path_expr.replace(p,
                    os.path.normpath(os.path.join(os.getcwd(), p))[1:])
        s["path"] = path_expr

        otb.merge(self.__dict__, s)

    def on_path_selected(self, new_path):

        matches = list(DataSource.SRC_PATTERN.finditer(self.path))

        self.use_expr = True
        if len(matches) == 0:
            self.path = "{" + new_path + "}"
        else:
            m = matches[0]
            self.path = (self.path[:m.start()]
                    + ("{" + new_path + "}") + self.path[m.end():])

    def __autogui__(self, name, ctx, sources):

        viz.push_id(name)

        if not self.allow_expr:
            self.use_expr = False

        if self.allow_expr and self.alt_val is not None:
            if viz.button(viz.Icon.ARROW_RIGHT_ARROW_LEFT):
                self.use_expr = not self.use_expr

            if viz.is_item_hovered():
                viz.begin_tooltip()
                if self.use_expr:
                    viz.text(f"Use alternative value: {str(self.alt_val)}")
                else:
                    viz.text("Use source expression")
                viz.end_tooltip()

            viz.same_line()

        if self.use_expr:
            if viz.button(viz.Icon.LIST):
                DataSource.SOURCES.request_selection_dialog(
                        self.on_path_selected, self.get_source_path())
            if viz.is_item_hovered():
                viz.begin_tooltip()
                viz.text("Select data source")
                viz.end_tooltip()

            viz.same_line()

        if self.use_expr:
            self.path = ctx.render(self.path, f"{name}###{name}source")
            if self.new_path is not None:
                self.path = self.new_path
                self.new_path = None
        else:
            self.render_alt_value(name, ctx)

        DataSource.SOURCES.render_selection_dialog()

        viz.pop_id()

        return self

    def render_alt_value(self, name, ctx):

        self.alt_val = ctx.render(self.alt_val, f"{name}###{name}source")

    def readwrite(self):

        m = DataSource.SRC_PATTERN.fullmatch(self.path)
        if m is None:
            return False

        src = DataSource.SOURCES[m.group(1)]
        if src is None:
            return False

        if not hasattr(src, "__autogui__"):
            return False

        return True

    def get_source_path(self):

        matches = list(DataSource.SRC_PATTERN.finditer(self.path))
        if len(matches) == 0:
            return ""

        return matches[0].group(1)

    def get_used_source(self):

        path = self.get_source_path()
        if path == "":
            return None

        return DataSource.SOURCES[path]

    def mod(self):
        
        s = self.get_used_source()
        if s is None:
            return True

        try:
            return s.mod
        except AttributeError:
            return True

    def set_mod(self):

        s = self.get_used_source()
        if s is None:
            return

        s.mod_requested = True

    def __call__(self):

        if self.use_expr:

            s = self.get_used_source()

            if s is not None:
                locs = {
                    "__src__": s,
                    "__alt__": self.alt_val
                }
            else:
                locs = {
                    "__alt__": self.alt_val
                }

            res_expr = self.path
            res_expr = DataSource.SRC_PATTERN.sub(
                    f'(__src__.data)', res_expr, 1)
            res_val = eval(res_expr, DataSource.SRC_GLOBALS, locs)
        else:
            res_val = self.alt_val

        return res_val

    def set(self, value):

        if not self.use_expr:
            self.alt_val = value
            return

        if not self.readwrite():
            return

        self.get_used_source().data = value


class ColorEdit(DataSource):

    def __init__(self, default=np.array([1.0, 1.0, 1.0, 1.0]), use_expr=False, allow_expr=False):

        super().__init__(default, use_expr, allow_expr)

    def render_alt_value(self, name, ctx):

        self.alt_val = viz.color_edit(f"{name}###{name}source", self.alt_val)


class PathSelector(DataSource):

    def __init__(self, default="./", use_expr=False, allow_expr=False):

        super().__init__(default, use_expr, allow_expr)

    def render_alt_value(self, name, ctx):

        self.alt_val = viz.file_dialog_popup("Select path", self.alt_val)
        if viz.button(viz.Icon.FOLDER_OPEN):
            viz.open_popup("Select path")
        viz.same_line()
        self.alt_val = viz.input(f"{name}###{name}source", self.alt_val)


class SelectHook:

    def __init__(self, sources_manager, base_path):

        self.sources_manager = sources_manager
        self.base_path = base_path

    def hook(self, _, name, ctx):

        if viz.is_item_hovered() and viz.is_mouse_double_clicked(0):
            if ctx is not None:
                elements = [str(e) for e in ctx.path]
            else:
                elements = []
            self.sources_manager.select(os.path.join(self.base_path, *elements))


def get_subclasses_recursive(cls):

    classes = []

    for c in cls.__subclasses__():
        cs = get_subclasses_recursive(c)
        classes += cs
        classes.append(c)

    return classes


class ViewBase:

    def __init__(self):

        self.uuid = uuid.uuid4().hex
        self.show = True
        self.destroyed = False


MENU_NAME_REGEX = re.compile(r"(?<=\w)([A-Z])")

def to_menu_name(name):

    name = MENU_NAME_REGEX.sub(r" \1", name)
    return name[0].upper() + name[1:].lower()

    
class FfmpegRecorder:

    def __init__(self,
                 path,
                 width,
                 height,
                 framerate=24,
                 bitrate='10M',
                 fmt='rgb24'):

        cmd = [
            '/usr/bin/ffmpeg',
            '-y',
            '-f', 'rawvideo',
            '-s', f'{int(width)}x{int(height)}', 
            '-pix_fmt', 'rgb24',
            '-r', str(framerate), 
            '-i', '-', 
            '-vcodec', 'mpeg4',
            '-b:v', bitrate,
            f'{path}'
        ]

        self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

    def record(self, frame):

        if self.proc.returncode is None:
            self.proc.stdin.write(frame[:, :, :3].tobytes())

    def finish(self):

        self.proc.communicate()


OBJ_CLIPBOARD_PREFIX = "__imdashclip__"


def check_obj_clipboard(tag=None):

    clipstr = viz.get_clipboard()
    if not clipstr.startswith(OBJ_CLIPBOARD_PREFIX):
        return False
    clipstr = clipstr[len(OBJ_CLIPBOARD_PREFIX):]

    try:
        if tag is not None:
            clipjson = json.loads(clipstr)
            if clipjson["tag"] != tag:
                return False
    except:
        traceback.print_exc()
        return False

    return True


def get_obj_clipboard(tag=None):

    clipstr = viz.get_clipboard()
    if not clipstr.startswith(OBJ_CLIPBOARD_PREFIX):
        return None
    clipstr = clipstr[len(OBJ_CLIPBOARD_PREFIX):]

    try:
        clipjson = json.loads(clipstr)
        if tag is not None and clipjson["tag"] != tag:
            return None
        objjson = json.loads(clipjson["data"])
        lod = otb.Loader("", mmap_arrays=False)
        obj = lod.load(None, objjson)
        return obj
    except:
        traceback.print_exc()

    return None


def set_obj_clipboard(obj, tag=""):

    clipstr = json.dumps({
        "tag": tag,
        "data": otb.saves(obj)
    })
    clipstr = OBJ_CLIPBOARD_PREFIX + clipstr
    viz.set_clipboard(clipstr)


def compute_file_hash(path):

    with open(path,"rb") as fd:
        f_data = fd.read()

    hasher = hashlib.sha1()
    hasher.update(f_data)

    return hasher.hexdigest()
