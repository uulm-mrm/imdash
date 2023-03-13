import ros2_numpy

import numpy as np
import imviz as viz


class ImageViewSource:

    def __init__(self):

        self.topic_name = ""
        self.flip_horizontally = False
        self.flip_vertically = False
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.x_scale = 1.0
        self.y_scale = 1.0


class ImageView:

    def __init__(self):

        self.show = True
        self.sources = []

    def render_settings(self, subs):

        viz.push_id(str(id(self)))

        sub_list = list(subs.values())
        topic_names = [s.topic_name for s in sub_list]

        self.show = viz.checkbox("show", self.show)

        if viz.tree_node(f"sources [{len(self.sources)}]###sources"):

            idx = viz.combo("add source", ["None"] + topic_names)
            if viz.mod() and idx > 0:
                ivs = ImageViewSource()
                ivs.topic_name = topic_names[idx - 1]
                self.sources.append(ivs)

            remove_list = []
            for ivs in self.sources:
                tree_open = viz.tree_node(f"{ivs.topic_name}###{id(ivs)}")
                if viz.begin_popup_context_item():
                    if viz.menu_item("Remove"):
                        remove_list.append(ivs)
                    viz.end_popup()
                if tree_open:
                    viz.autogui(ivs)
                    viz.tree_pop()
            viz.tree_pop()

            for ivs in remove_list:
                self.sources.remove(ivs)

        viz.pop_id()
        
    def render(self, subs):

        if not self.show:
            return

        if viz.begin_figure(f"ImageView###view_{id(self)}", 
                flags=viz.PlotFlags.NO_TITLE | viz.PlotFlags.EQUAL):

            self.show = viz.get_window_open()

            for s in self.sources:

                if s.topic_name not in subs:
                    continue

                ds = subs[s.topic_name]

                if ds.topic_type_name != "sensor_msgs/msg/Image":
                    continue

                if ds.latest_msg is None:
                    continue

                img = ros2_numpy.numpify(ds.latest_msg)

                if s.flip_vertically and s.flip_horizontally:
                    img = img[::-1, ::-1].copy()
                elif s.flip_vertically:
                    img = img[::-1, :].copy()
                elif s.flip_horizontally:
                    img = img[:, ::-1].copy()

                viz.plot_image(
                        s.topic_name,
                        img,
                        s.x_offset, s.y_offset,
                        img.shape[1] * s.x_scale, img.shape[0] * s.y_scale)

        viz.end_figure()


def project_points_into_view(view, proj, pc):

    if pc.ndim == 1:
        pc_x = pc[:]["x"].reshape(-1, 1)
        pc_y = pc[:]["y"].reshape(-1, 1)
        pc_z = pc[:]["z"].reshape(-1, 1)
    else:
        pc_x = pc[:, :]["x"].reshape(-1, 1)
        pc_y = pc[:, :]["y"].reshape(-1, 1)
        pc_z = pc[:, :]["z"].reshape(-1, 1)
    pc_w = np.ones(len(pc_z), dtype=np.float32).reshape(-1, 1)
    pc_hom = np.concatenate((pc_x, pc_y, pc_z, pc_w), axis=1)

    # extract distance as measured by lidar
    if 'range' in pc.dtype.names:
        if pc.ndim == 1:
            pc_range = pc[:]["range"].reshape(-1, 1)
        else:
            pc_range = pc[:, :]["range"].reshape(-1, 1)
    else:
        pc_range = np.sqrt(pc_x ** 2 + pc_y ** 2 + pc_z ** 2)

    # transform into camera coordinate system
    cps = np.einsum('ij,kj->ik', pc_hom, view)

    # project points onto image plane
    pps = np.einsum('ij,kj->ki', proj, cps[:, :3])
    pps = np.where(pps[:, 2:3] > 10e-5, pps / pps[:, 2:3], pps)

    return pps
