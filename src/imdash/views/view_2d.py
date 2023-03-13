import copy
import uuid
import textwrap
import traceback

import numpy as np
import imviz as viz

from imdash.utils import (
    ViewBase,
    DataSource,
    ColorEdit,
    to_menu_name
)

import imdash.utils as utils


class View2DComponent:

    DISPLAY_NAME = None

    def __init__(self):
        self.uuid = uuid.uuid4().hex
        self.label = "unnamed_component"
        self.hide_on_error = False
        self.no_fit = False

    def update(self, idx, view):
        # called every frame
        # implement logic here
        pass

    def render(self, idx, view):
        # called if component is visible
        # implement rendering here
        pass


class PlotSettings:

    def __init__(self):

        self.title = "View2D"

        self.x_label = ""
        self.y_label = ""

        self.flags = viz.PlotFlags.NO_TITLE | viz.PlotFlags.NO_MOUSE_TEXT
        self.plot_limits = []

        self.auto_fit_x = False
        self.auto_fit_y = False
        self.lock_axis_x = False
        self.lock_axis_y = False
        self.auto_fit_padding_x = 1.0
        self.auto_fit_padding_y = 1.0
        self.show_axis_x = True
        self.show_axis_y = True

    def tooltip(self, text):

        if viz.is_item_hovered():
            viz.begin_tooltip()
            viz.text(text)
            viz.end_tooltip()

    def __autogui__(self, name, ctx, **kwargs):

        self.title = ctx.render(self.title, "title")
        self.x_label = ctx.render(self.x_label, "x_label")
        self.y_label = ctx.render(self.y_label, "y_label")

        self.show_axis_x = ctx.render(self.show_axis_x, f"show {viz.Icon.X}")
        viz.same_line()
        if self.lock_axis_x:
            if viz.button(f"{viz.Icon.LOCK}###lock_x"):
                self.lock_axis_x = False
            self.tooltip("Unlock X-Axis")
        else:
            if viz.button(f"{viz.Icon.LOCK_OPEN}###lock_x"):
                self.auto_fit_x = False
                self.lock_axis_x = True
            self.tooltip("Lock X-Axis")
        viz.same_line()
        if self.auto_fit_x:
            if viz.button(f"{viz.Icon.EXPAND}###autofit_x"):
                self.auto_fit_x = False
            self.tooltip("Pan X-Axis")
        else:
            if viz.button(f"{viz.Icon.UP_DOWN_LEFT_RIGHT}###no_autofit_x"):
                self.auto_fit_x = True
                self.lock_axis_x = False
            self.tooltip("Autofit X-Axis")

        self.show_axis_y = ctx.render(self.show_axis_y, f"show {viz.Icon.Y}")
        viz.same_line()
        if self.lock_axis_y:
            if viz.button(f"{viz.Icon.LOCK}###lock_y"):
                self.lock_axis_y = False
            self.tooltip("Unlock Y-Axis")
        else:
            if viz.button(f"{viz.Icon.LOCK_OPEN}###unlock_y"):
                self.auto_fit_y = False
                self.lock_axis_y = True
            self.tooltip("Lock Y-Axis")
        viz.same_line()
        if self.auto_fit_y:
            if viz.button(f"{viz.Icon.EXPAND}###autofit_y"):
                self.auto_fit_y = False
            self.tooltip("Pan Y-Axis")
        else:
            if viz.button(f"{viz.Icon.UP_DOWN_LEFT_RIGHT}###no_autofit_y"):
                self.auto_fit_y = True
                self.lock_axis_y = False
            self.tooltip("Autofit Y-Axis")


class View2D(ViewBase):

    def __init__(self):

        super().__init__()

        self.plot_settings = PlotSettings()
        self.components = []

    @property
    def title(self):
        return self.plot_settings.title

    @title.setter
    def title(self, value):
        self.plot_settings.title = value

    def render_components(self, sources):

        remove_item = None
        copy_item = None
        duplicate_item = None
        move_item = None

        def comp_menu_funcs(c, i):
            nonlocal remove_item
            nonlocal copy_item
            nonlocal duplicate_item
            nonlocal move_item
            if viz.begin_menu("Render order"):
                if viz.menu_item("To top"):
                    move_item = (len(self.components)-1, c)
                if viz.menu_item("Up"):
                    move_item = (min(len(self.components)-1, i+1), c)
                if viz.menu_item("Down"):
                    move_item = (max(0, i-1), c)
                if viz.menu_item("To bottom"):
                    move_item = (0, c)
                viz.end_menu()
            if viz.menu_item("Copy"):
                copy_item = i
            if viz.menu_item("Duplicate"):
                duplicate_item = i
            if viz.menu_item("Delete"):
                remove_item = i

        for i, c in enumerate(self.components):
            exc = None
            try:
                c.render(c.uuid, self)
                label_id = c.label + f"###{c.uuid}"
            except Exception as e:
                label_id = c.label + f" {viz.Icon.TRIANGLE_EXCLAMATION}" + f"###{c.uuid}"
                if not c.hide_on_error:
                    viz.plot_dummy(label_id, legend_color=(1.0, 0.0, 0.0))
                exc = traceback.format_exc()
            if viz.begin_legend_popup(label_id):
                if exc is not None:
                    if viz.begin_menu("Error"):
                        exc = "\n".join(["\n".join(textwrap.wrap(
                            l,
                            100,
                            subsequent_indent=" "*8,
                            break_on_hyphens=False))
                            for l in exc.split("\n")])
                        viz.text(exc)
                        viz.end_menu()
                if viz.begin_menu("Edit"):
                    viz.autogui(c, name="", sources=sources)
                    viz.end_menu()
                comp_menu_funcs(c, i)
                viz.end_legend_popup()

        if viz.begin_plot_popup():
            if utils.check_obj_clipboard("View2DComponent"):
                if viz.menu_item("Paste"):
                    obj = utils.get_obj_clipboard("View2DComponent")
                    if isinstance(obj, View2DComponent):
                        obj.uuid = uuid.uuid4().hex
                        self.components.append(obj)
                viz.separator()
            if viz.begin_menu("Properties"):
                viz.autogui(self.plot_settings, "", sources=sources)
                viz.end_menu()
            if viz.begin_menu("Components"):
                for i, c in enumerate(self.components):
                    if c.label == "":
                        c_name = f"component_#{i}###{c.uuid}"
                    else:
                        c_name = f"{c.label}###{c.uuid}"
                    menu_open = viz.begin_menu(c_name)
                    if viz.begin_popup_context_item():
                        comp_menu_funcs(c, i)
                        viz.end_legend_popup()
                    if menu_open:
                        viz.push_id(c_name)
                        viz.autogui(c, name="", sources=sources)
                        viz.pop_id()
                        viz.end_menu()
                viz.end_menu()
            if viz.begin_menu("Create"):
                cls_names = []
                for cls in View2DComponent.__subclasses__():
                    name = (cls.DISPLAY_NAME 
                            if cls.DISPLAY_NAME is not None else cls.__name__)
                    cls_names.append((name, cls))
                cls_names.sort(key=lambda x: x[0])
                for name, cls in cls_names:
                    parts = name.split("/")
                    depth = 0
                    for i, p in list(enumerate(parts)):
                        if i == len(parts)-1:
                            if viz.menu_item(parts[-1]):
                                self.components.append(cls())
                                viz.set_mod(True)
                        elif viz.begin_menu(p):
                            depth += 1
                        else:
                            break
                    for d in range(depth):
                        viz.end_menu()
                viz.end_menu()
            viz.separator()
            if viz.menu_item("Delete view"):
                self.destroyed = True
            viz.separator()
        viz.end_plot_popup()

        # update components

        if remove_item is not None:
            self.components.pop(remove_item)
            viz.set_mod(True)
        if copy_item is not None:
            utils.set_obj_clipboard(self.components[copy_item],
                                    tag="View2DComponent")
        if duplicate_item is not None:
            dup = copy.deepcopy(self.components[duplicate_item])
            dup.uuid = uuid.uuid4().hex
            self.components.insert(duplicate_item, dup)
            viz.set_mod(True)
        if move_item is not None:
            self.components.remove(move_item[1])
            self.components.insert(move_item[0], move_item[1])
            viz.set_mod(True)

    def setup_axes(self):

        ps = self.plot_settings
        pl = ps.plot_limits

        if len(pl) == 4:
            viz.setup_axes_limits(pl[0], pl[2], pl[1], pl[3])

        x_axis_flags = viz.PlotAxisFlags.NONE
        if ps.auto_fit_x:
            x_axis_flags |= viz.PlotAxisFlags.AUTO_FIT
        if not ps.show_axis_x:
            x_axis_flags |= viz.PlotAxisFlags.NO_DECORATIONS
            x_axis_flags &= ~viz.PlotAxisFlags.NO_GRID_LINES
        viz.setup_axis(viz.Axis.X1, ps.x_label, flags=x_axis_flags)
        if ps.lock_axis_x:
            viz.setup_axis_limits(viz.Axis.X1, pl[0], pl[2], flags=viz.PlotCond.ALWAYS)

        y_axis_flags = viz.PlotAxisFlags.NONE
        if ps.auto_fit_y:
            y_axis_flags |= viz.PlotAxisFlags.AUTO_FIT
        if not ps.show_axis_y:
            y_axis_flags |= viz.PlotAxisFlags.NO_DECORATIONS
            y_axis_flags &= ~viz.PlotAxisFlags.NO_GRID_LINES
        viz.setup_axis(viz.Axis.Y1, ps.y_label, flags=y_axis_flags)
        if ps.lock_axis_y:
            viz.setup_axis_limits(viz.Axis.Y1, pl[1], pl[3], flags=viz.PlotCond.ALWAYS)

        # scroll -> update autofit percentage

        for se in viz.get_scroll_events():
            if se.yoffset < 0:
                f = abs(se.yoffset) * 1.1
                if ps.auto_fit_x and viz.is_axis_hovered(viz.Axis.X1):
                    ps.auto_fit_padding_x *= f
                    viz.set_mod(True)
                if ps.auto_fit_y and viz.is_axis_hovered(viz.Axis.Y1):
                    ps.auto_fit_padding_y *= f
                    viz.set_mod(True)
                if ps.auto_fit_x and ps.auto_fit_y and viz.is_plot_hovered():
                    if viz.is_axis_hovered(viz.Axis.X1):
                        ps.auto_fit_padding_x *= f
                        viz.set_mod(True)
                    elif viz.is_axis_hovered(viz.Axis.Y1):
                        ps.auto_fit_padding_y *= f
                        viz.set_mod(True)
                    else:
                        ps.auto_fit_padding_x *= f
                        ps.auto_fit_padding_y *= f
                        viz.set_mod(True)
            elif se.yoffset > 0:
                f = abs(se.yoffset) * 1.1
                if ps.auto_fit_x and viz.is_axis_hovered(viz.Axis.X1):
                    ps.auto_fit_padding_x /= f
                    viz.set_mod(True)
                if ps.auto_fit_y and viz.is_axis_hovered(viz.Axis.Y1):
                    ps.auto_fit_padding_y /= f
                    viz.set_mod(True)
                if ps.auto_fit_x and ps.auto_fit_y and viz.is_plot_hovered():
                    if viz.is_axis_hovered(viz.Axis.X1):
                        ps.auto_fit_padding_x /= f
                        viz.set_mod(True)
                    elif viz.is_axis_hovered(viz.Axis.Y1):
                        ps.auto_fit_padding_y /= f
                        viz.set_mod(True)
                    else:
                        ps.auto_fit_padding_x /= f
                        ps.auto_fit_padding_y /= f
                        viz.set_mod(True)

        # double click -> snap back to autofit

        if viz.is_mouse_double_clicked(0):
            if viz.is_axis_hovered(viz.Axis.X1):
                ps.auto_fit_padding_x = 1.0
                ps.auto_fit_x = True
                viz.set_mod(True)
            elif viz.is_axis_hovered(viz.Axis.Y1):
                ps.auto_fit_padding_y = 1.0
                ps.auto_fit_y = True
                viz.set_mod(True)
            elif viz.is_plot_hovered():
                ps.auto_fit_padding_x = 1.0
                ps.auto_fit_padding_y = 1.0
                ps.auto_fit_x = True
                ps.auto_fit_y = True
                viz.set_mod(True)

        # mouse drag -> disable autofit

        if not (viz.get_mouse_drag_delta() == 0.0).all():
            if viz.is_axis_hovered(viz.Axis.X1):
                ps.auto_fit_x = False
                viz.set_mod(True)
            elif viz.is_axis_hovered(viz.Axis.Y1):
                ps.auto_fit_y = False
                viz.set_mod(True)
            elif viz.is_plot_hovered():
                ps.auto_fit_x = False
                ps.auto_fit_y = False
                viz.set_mod(True)

    def render(self, sources):

        if not self.show:
            return

        viz.push_plot_style_var(
                viz.PlotStyleVar.FIT_PADDING, 
                (self.plot_settings.auto_fit_padding_x - 1.0,
                    self.plot_settings.auto_fit_padding_y - 1.0))

        figure_flags = self.plot_settings.flags | viz.PlotFlags.NONE

        window_open = viz.begin_figure(
                f"{self.plot_settings.title}###{self.uuid}",
                flags=figure_flags)

        self.show = viz.get_window_open()

        if window_open:

            self.setup_axes()
            self.render_components(sources)

            # reconvert plot flags

            self.plot_settings.flags = int(viz.get_plot_flags())
            self.plot_settings.plot_limits = viz.get_plot_limits()

        viz.end_figure()

        viz.pop_plot_style_var(1)
