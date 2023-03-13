import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.components.view_2d.point_cloud import transform_point_cloud
from imdash.utils import DataSource, ColorEdit

import matplotlib


def project_points_into_view(view, proj, cloud, min_range=0.0, max_range=float("inf")):

    cloud_cc = transform_point_cloud(view, cloud)

    # restrict range
    cloud_cc = cloud_cc[(min_range <= cloud_cc[:, 2])
                         & (cloud_cc[:, 2] <= max_range), :]

    # relative z for coloring
    cloud_cc_z_rel = (cloud_cc[:, 2] - min_range) / (max_range - min_range)

    # project points to image coordinates
    cloud_ic = (proj @ cloud_cc[:, :3].T).T
    cloud_ic = cloud_ic[np.abs(cloud_ic[:, 2]) > 1e-6, :]
    cloud_ic = cloud_ic[:, :2] / cloud_ic[:, 2:3]

    return cloud_ic, cloud_cc_z_rel


class PointCloudProj2DComp(View2DComponent):

    DISPLAY_NAME = "ROS2/Point cloud projector"

    def __init__(self):

        super().__init__()

        self.lidar_source = DataSource(default=[0.0, 1.0, 2.0])
        self.cam_info_source = DataSource(default=[0.0, 1.0, 2.0])

        self.z_min = DataSource(default=0.0, use_expr=False)
        self.z_max = DataSource(default=100.0, use_expr=False)

        self.marker_size = 3.0
        self.use_color_map = False

        self.color = ColorEdit(default=np.array([1.0, 0.0, 0.0]))
        self.opacity = 1.0

    def render(self, idx, view):

        ros_con = DataSource.SOURCES.connectors[1]

        pc_np = self.lidar_source()
        pc = self.lidar_source.get_used_source()

        cam_info = self.cam_info_source()

        view = ros_con.get_tf_mat(pc.last_msg.msg.header.frame_id,
                                  cam_info.header.frame_id,
                                  cam_info.header.stamp)

        proj = np.array(cam_info.p, dtype='float32').reshape(3, 4)[:, :3]
        w = cam_info.width
        h = cam_info.height

        z_min = self.z_min()
        z_max = self.z_max()

        ppc, ppc_rel_z = project_points_into_view(
                view, proj, pc_np, z_min, z_max)
        ppc[:, 1] = h - ppc[:, 1]

        in_img_idx = ((ppc[:, 0] < w)
                      & (0 < ppc[:, 0])
                      & (ppc[:, 1] < h)
                      & (0 < ppc[:, 1]))

        ppc = ppc[in_img_idx, :]
        ppc_rel_z = ppc_rel_z[in_img_idx]

        self.opacity = max(0.0, min(1.0, self.opacity))
        if self.use_color_map:
            cmap = matplotlib.colormaps.get_cmap('hsv')
            color = cmap(ppc_rel_z)
            color[:, 3] = self.opacity
        else:
            color = (*self.color(), self.opacity)

        flags = viz.PlotLineFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT

        viz.plot(ppc[:, 0],
                 ppc[:, 1],
                 fmt="o",
                 label=f"{self.label}###{idx}",
                 marker_size=self.marker_size,
                 color=color,
                 flags=flags)
