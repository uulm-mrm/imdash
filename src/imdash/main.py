import os
import sys
import time
import copy
import glob
import shutil

import numpy as np
import imviz as viz
import objtoolbox as otb

import imdash.utils as utils
from imdash.connectors import ConnectorBase

from PIL import Image


APPLICATION_NAME = "imdash"
GLOBAL_CONF_DIR = os.path.expanduser(f"~/.config/{APPLICATION_NAME}")
DEFAULT_CONF_PATH = os.path.join(GLOBAL_CONF_DIR, "config_store", "default")


class GlobalConfig:

    def __init__(self):

        self.menu_file_path = "./"
        self.last_config_path = None


class SourcesManager:

    def __init__(self, *args, **kwargs):

        self.sources = {}
        self.is_alive = {}

        self.last_selected = ""

        self.dialog_requested = False
        self.dialog_path = ""
        self.selection_callback = None

        con_clss = utils.get_subclasses_recursive(ConnectorBase)
        self.connectors = [cls() for cls in con_clss]

    def request_selection_dialog(self, selection_callback, dialog_path):

        self.dialog_requested = True
        self.dialog_path = dialog_path
        self.selection_callback = selection_callback

    def reinit(self):

        self.sources = {}
        self.is_alive = {}

        self.last_selected = ""

        for c in self.connectors:
            c.cleanup()

    def check_selection(self):

        return viz.is_item_hovered() and viz.is_mouse_double_clicked(0)

    def select(self, selection):

        self.last_selected = selection
        self.selection_callback(selection)
        viz.set_mod(True)

    def update(self):

        for con in self.connectors:
            con.update_sources(self)

    def render_selection_dialog(self):

        if self.dialog_requested:
            viz.open_popup("Select source")
            self.dialog_requested = False

        self.last_selected = self.dialog_path

        viz.set_next_window_size(viz.get_main_window_size() * 0.5)
        if viz.begin_popup_modal(f"Select source"):
            r = viz.get_content_region_avail()
            h = r[1] - viz.get_global_font_size() * 1.8
            if viz.begin_child("connectors", size=(-1, h)):
                for con in self.connectors:
                    con.render(None, self)
                if viz.is_mouse_double_clicked(0):
                    viz.close_current_popup()
                viz.end_child()
            viz.separator()
            if viz.button("Cancel"):
                viz.close_current_popup()
            viz.same_line()
            viz.text("Hint: Select with double click")
            viz.end_popup()

    def reset_liveness(self):
        new_sources = {}
        for k, v in self.sources.items():
            if self.is_alive[k]:
                new_sources[k] = v
            else:
                try:
                    v.cleanup()
                except AttributeError:
                    pass
        self.sources = new_sources
        self.is_alive = {k: False for k in self.keys()}

    def items(self):
        return self.sources.items()

    def keys(self):
        return self.sources.keys()

    def values(self):
        return self.sources.values()

    def __len__(self):
        return len(self.sources)

    def __getitem__(self, key, default_init=lambda: None):

        try:
            val = self.sources[key]
        except KeyError:
            self.sources[key] = default_init()
            val = self.sources[key]

        self.is_alive[key] = True

        return val

    def __delitem__(self, key):
        del self.sources[key]

    def __setitem__(self, key, value):
        self.sources[key] = value

    def __contains__(self, key):
        return key in self.sources


class Main:

    def __init__(self):

        res_path = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), "resources")

        with Image.open(os.path.join(res_path, "logo.png")) as img:
            logo = np.asarray(img).copy()
        viz.set_main_window_icon(logo)

        self.window_pos = np.array([100, 100])
        self.window_size = np.array([800, 600])

        # config handling
        self.file_path_required = False
        self.menu_file_func = None
        self.config_name_required = False
        self.config_name_func = None
        self.config_name_tmp = ""
        self.config_delete_required = False
        self.config_path = None
        self.window_config = ""

        # if a config was imported this contains a hash
        # of the original config that was imported
        self.imported_config_hash = None

        # tools
        self.screenshot_countdown = -1
        self.video_recorder = None

        # local settings
        self.paused = False
        self.vsync = True
        self.powersave = False
        self.autosave = True
        self.use_light_theme = False
        self.font_size = 20.0

        # initialize global configuration
        self.global_config = GlobalConfig()
        otb.load(self.global_config, GLOBAL_CONF_DIR)
        os.makedirs(GLOBAL_CONF_DIR, exist_ok=True)

        gc = self.global_config
        if gc.last_config_path is not None:
            self.open_config(gc.last_config_path)
        else:
            self.open_config(DEFAULT_CONF_PATH, True)

        # autosave and undo
        self.last_mod_time = time.time()
        self.save_needed = False
        self.undo_save_needed = False
        self.undo_stack = [copy.deepcopy(self.views)]
        self.undo_position = 0

    def __savestate__(self):

        d = self.__dict__.copy()
        exclude = [
            "global_config",
            "file_path_required", 
            "menu_file_func",
            "config_name_required",
            "config_name_func",
            "config_name_tmp",
            "config_path",
            "sources_manager",
            "last_mod_time",
            "auto_save_needed",
            "undo_save_needed",
            "undo_stack",
            "undo_position",
            "video_recorder",
        ]
        for e in exclude:
            try:
                del d[e]
            except KeyError:
                pass

        return d

    def reinit_views_and_sources(self):

        if hasattr(self, "sources_manager"):
            self.sources_manager.reinit()

        self.sources_manager = SourcesManager()
        self.views = {}

    def open_config(self, path, create_if_not_exists=False):

        self.reinit_views_and_sources()

        if not os.path.exists(path) or not os.path.isdir(path):
            if create_if_not_exists:
                self.save_config(path)
            else:
                self.config_path = None
                return False

        os.chdir(path)

        otb.load(self, path)
        self.config_path = os.path.realpath(path)
        viz.load_ini_from_str(self.window_config)

        self.global_config.last_config_path = self.config_path
        otb.save(self.global_config, GLOBAL_CONF_DIR)

        viz.set_main_window_pos(self.window_pos)
        viz.set_main_window_size(self.window_size)

        return True

    def save_config(self, path=None):

        if path is not None:
            self.config_path = os.path.realpath(path)

        if self.config_path is None:
            return False

        self.window_pos = viz.get_main_window_pos()
        self.window_size = viz.get_main_window_size()

        os.makedirs(self.config_path, exist_ok=True)
        os.chdir(self.config_path)

        self.window_config = viz.save_ini_to_str()
        otb.save(self, self.config_path)

        self.global_config.last_config_path = self.config_path
        otb.save(self.global_config, GLOBAL_CONF_DIR)
        
        self.save_needed = False

        return True

    def import_config(self, path, overwrite=True):

        import_hash = utils.compute_file_hash(os.path.join(path, "state.json"))
        import_config_path = os.path.join(GLOBAL_CONF_DIR, "config_store", os.path.basename(path))
        config_exists = self.open_config(import_config_path)

        if not config_exists or overwrite or import_hash != self.imported_config_hash:
            self.open_config(path)
            self.imported_config_hash = import_hash
            self.save_config(import_config_path)
            self.open_config(import_config_path)

    def export_config(self, path):

        self.window_pos = viz.get_main_window_pos()
        self.window_size = viz.get_main_window_size()

        os.makedirs(path, exist_ok=True)
        os.chdir(path)

        self.window_config = viz.save_ini_to_str()
        otb.save(self, path)

        otb.save(self.global_config, GLOBAL_CONF_DIR)

        return True

    def update_main_window(self):

        if not viz.wait(vsync=self.vsync, powersave=self.powersave):
            if self.autosave and self.config_path is not None:
                self.save_config()
            sys.exit(0)

        if self.use_light_theme:
            viz.style_colors_light()
        else:
            viz.style_colors_dark()

        viz.set_global_font_size(self.font_size)

        config_name = "no config"
        if self.config_path is not None:
            config_name = os.path.basename(self.config_path)
        viz.set_main_window_title(
                f"{APPLICATION_NAME} - {config_name}"
                + ("*" if self.save_needed else "")
                + (" - [RECORDING]" if self.video_recorder is not None else "")
                + (" - [PAUSED]" if self.paused else ""))

    def update_tools(self):

        if self.screenshot_countdown == 0:
            frame = viz.get_pixels(0, 0, *viz.get_main_window_size())[:,:,:3]
            img = Image.fromarray(frame)
            self.trigger_file_request(lambda: img.save(self.global_config.menu_file_path))

        if self.screenshot_countdown > -1:
            self.screenshot_countdown -= 1

        if self.video_recorder is not None:
            frame = viz.get_pixels(0, 0, *viz.get_main_window_size())
            self.video_recorder.record(frame)

    def update_views_and_sources(self):

        utils.DataSource.SOURCES = self.sources_manager

        if not self.paused:
            self.sources_manager.update()

        self.sources_manager.reset_liveness()

        viz.push_mod_any()

        remove_views = []

        for k, v in self.views.items():
            if v.destroyed:
                remove_views.append(k)
            else:
                v.render(self.sources_manager)

        for k in remove_views:
            viz.set_mod(True)
            del self.views[k]

    def update_main_menu(self):

        if viz.begin_main_menu_bar():
            if viz.begin_menu("File"):
                if viz.menu_item("New"):
                    self.config_path = None
                    self.reinit_views_and_sources()
                    self.trigger_config_name_request(lambda path: self.open_config(path, True))
                if viz.menu_item("Save", shortcut="Ctrl+S", enabled=self.config_path is not None):
                    self.save_config()
                if viz.menu_item("Save as"):
                    self.trigger_config_name_request(
                            lambda path: self.save_config(path))
                viz.separator()
                if viz.menu_item("Import"):
                    self.trigger_file_request(
                            lambda: self.import_config(
                                self.global_config.menu_file_path))
                if viz.menu_item("Export"):
                    self.trigger_file_request(
                            lambda: self.export_config(
                                self.global_config.menu_file_path))
                viz.separator()
                if viz.menu_item("Delete config"):
                    self.config_delete_required = True
                viz.end_menu()
            if viz.begin_menu("Configs"):
                avail_configs = glob.glob(os.path.join(GLOBAL_CONF_DIR, "config_store", "*"))
                avail_configs = sorted(avail_configs)
                for p in avail_configs:
                    config_name = os.path.basename(p)
                    if viz.menu_item(config_name, selected=(p == self.config_path)):
                        self.open_config(p)
                viz.end_menu()
            if viz.begin_menu("Edit"):
                if viz.menu_item("Undo",
                        shortcut="Ctrl+Z",
                        enabled=self.undo_position > 0):
                    self.undo_edit()
                if viz.menu_item("Redo",
                        shortcut="Ctrl+Y",
                        enabled=self.undo_position < len(self.undo_stack)-1):
                    self.redo_edit()
                viz.end_menu()
            if viz.begin_menu("Views"):
                if viz.begin_menu("Create"):
                    view_classes = utils.get_subclasses_recursive(utils.ViewBase)
                    view_classes.sort(key=lambda cls: cls.__name__)
                    for cls in view_classes:
                        if viz.menu_item(cls.__name__):
                            view_obj = cls()
                            self.views[view_obj.uuid] = view_obj
                            viz.set_mod(True)
                    viz.end_menu()
                if viz.begin_menu("Show"):
                    for v in sorted(self.views.values(), key=lambda x: x.title):
                        if viz.menu_item(v.title, selected=v.show):
                            v.show = not v.show
                    viz.end_menu()
                viz.end_menu()
            if viz.begin_menu("Tools"):
                if viz.menu_item("Screenshot"):
                    self.screenshot_countdown = 2
                if self.video_recorder is None:
                    if viz.menu_item("Start video", shortcut="Ctrl+R"):
                        self.start_video_recording()
                else:
                    if viz.menu_item("Finish video", shortcut="Ctrl+R"):
                        self.video_recorder.finish()
                        self.video_recorder = None
                        self.trigger_file_request(self.finish_video_recording)
                viz.end_menu()
            if viz.begin_menu("Settings"):
                if viz.menu_item("Paused", selected=self.paused):
                    self.paused = not self.paused
                if viz.menu_item("Vsync", selected=self.vsync):
                    self.vsync = not self.vsync
                if viz.menu_item("Powersave", selected=self.powersave):
                    self.powersave = not self.powersave
                if viz.menu_item("Autosave",
                                 selected=self.autosave,
                                 enabled=self.config_path is not None):
                    self.autosave = not self.autosave
                if viz.menu_item("Use light theme", selected=self.use_light_theme):
                    self.use_light_theme = not self.use_light_theme
                self.font_size = max(10.0, viz.drag("Font size", self.font_size))
                viz.end_menu()
        viz.end_main_menu_bar()

    def update_keyboard_shortcuts(self):

        for ke in viz.get_key_events():
            if ke.key == viz.KEY_SPACE and ke.action == viz.PRESS and ke.mod == viz.MOD_CONTROL:
                self.paused = not self.paused
            if (ke.key == viz.KEY_S
                    and ke.action == viz.PRESS
                    and ke.mod == viz.MOD_CONTROL):
                self.save_config()
            if (ke.key == viz.KEY_R
                    and ke.action == viz.PRESS
                    and ke.mod == viz.MOD_CONTROL):
                if self.video_recorder is None:
                    self.start_video_recording()
                else:
                    self.video_recorder.finish()
                    self.video_recorder = None
                    self.trigger_file_request(self.finish_video_recording)
            if (ke.key == viz.KEY_Z
                    and ke.action == viz.PRESS
                    and ke.mod == viz.MOD_CONTROL):
                self.undo_edit()
            if (ke.key == viz.KEY_Y
                    and ke.action == viz.PRESS
                    and ke.mod == viz.MOD_CONTROL):
                self.redo_edit()

    def update_undo_and_autosave(self):

        now_time = time.time()

        if viz.pop_mod_any():
            self.last_mod_time = now_time
            self.undo_save_needed = True
            self.save_needed = True

        if now_time - self.last_mod_time > 0.5:
            if (self.save_needed
                    and self.autosave
                    and self.config_path is not None):
                self.save_config()
            if self.undo_save_needed:
                self.undo_stack = self.undo_stack[:self.undo_position+1]
                self.undo_stack.append(copy.deepcopy(self.views))
                self.undo_position += 1
                self.undo_save_needed = False

        while len(self.undo_stack) > 100:
            self.undo_stack.pop(0)

    def undo_edit(self):

        self.undo_position -= 1
        self.undo_position = max(0, min(
            len(self.undo_stack) - 1, self.undo_position))
        self.views = copy.deepcopy(self.undo_stack[self.undo_position])

    def redo_edit(self):

        self.undo_position += 1
        self.undo_position = max(0, min(
            len(self.undo_stack) - 1, self.undo_position))
        self.views = copy.deepcopy(self.undo_stack[self.undo_position])

    def start_video_recording(self):

        self.video_recorder = utils.FfmpegRecorder(
                '/tmp/imdash_tmp_recording.mp4',
                *viz.get_main_window_size()
            )

    def finish_video_recording(self):

        shutil.move('/tmp/imdash_tmp_recording.mp4',
                    self.global_config.menu_file_path)

    def trigger_file_request(self, func):

        self.file_path_required = True
        self.menu_file_func = func

    def handle_file_request(self):

        if self.file_path_required:
            viz.open_popup("menu_file_selection")

        self.global_config.menu_file_path = viz.file_dialog_popup(
            "menu_file_selection",
            self.global_config.menu_file_path)

        if viz.mod():
            self.menu_file_func()
            self.menu_file_func = None

        self.file_path_required = False

    def trigger_config_name_request(self, func):

        self.config_name_required = True
        self.config_name_func = func

    def handle_config_name_request(self):

        if self.config_name_required:
            viz.open_popup("Config name")

        done = False

        w, h = viz.get_main_window_size()
        viz.set_next_window_pos((w/2, h/2), viz.Cond.ALWAYS, (0.5, 0.5))

        if viz.begin_popup_modal("Config name"):
            self.config_name_tmp = viz.input("name", self.config_name_tmp)
            viz.separator()
            if viz.button("Ok"):
                done = True
                viz.close_current_popup()
            viz.same_line()
            if viz.button("Cancel"):
                viz.close_current_popup()
            viz.end_popup()

        if done:
            path = os.path.join(GLOBAL_CONF_DIR, "config_store", self.config_name_tmp)
            self.config_name_func(path)
            self.config_name_func = None

        self.config_name_required = False

    def handle_config_delete_request(self):

        if self.config_delete_required:
            viz.open_popup("Delete config")

        delete = False

        w, h = viz.get_main_window_size()
        viz.set_next_window_pos((w/2, h/2), viz.Cond.ALWAYS, (0.5, 0.5))

        if viz.begin_popup_modal("Delete config"):
            viz.text("Warning: The config will be permanently deleted. This cannot be undone.")
            viz.text("Are you sure you want to delete the current config?")
            viz.separator()
            if viz.button("Ok"):
                delete = True
                viz.close_current_popup()
            viz.same_line()
            if viz.button("Cancel"):
                viz.close_current_popup()
            viz.end_popup()

        if delete:
            shutil.rmtree(self.config_path)
            self.config_path = None
            self.global_config.last_config_path = None
            self.reinit_views_and_sources()

        self.config_delete_required = False

    def loop(self):

        while True:
            self.update()

    def update(self):

        self.update_main_window()
        self.update_tools()
        self.update_views_and_sources()
        self.update_main_menu()
        self.update_keyboard_shortcuts()
        self.update_undo_and_autosave()
        self.handle_file_request()
        self.handle_config_name_request()
        self.handle_config_delete_request()


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--dev":
        viz.dev.launch(Main, "update")
    else:
        Main().loop()


if __name__ == "__main__":
    main()
