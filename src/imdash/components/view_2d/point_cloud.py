import numpy as np
import imviz as viz

from imdash.views.view_2d import View2DComponent
from imdash.utils import DataSource, ColorEdit


def transform_point_cloud(view, cloud):

    # extract cloud coordinates
    if cloud.ndim == 1:
        cloud_x = cloud[:]['x'].reshape(-1, 1)
        cloud_y = cloud[:]['y'].reshape(-1, 1)
        cloud_z = cloud[:]['z'].reshape(-1, 1)
    else:
        cloud_x = cloud[:, :]['x'].reshape(-1, 1)
        cloud_y = cloud[:, :]['y'].reshape(-1, 1)
        cloud_z = cloud[:, :]['z'].reshape(-1, 1)
    cloud_hom = np.concatenate((cloud_x, cloud_y, cloud_z, np.ones(cloud_x.shape)), axis=1)

    cloud_cc = (view @ cloud_hom.T).T

    return cloud_cc


class PointCloud2DComp(View2DComponent):

    DISPLAY_NAME = "ROS2/Point cloud"

    def __init__(self):

        super().__init__()

        self.point_cloud_source = DataSource(default=[0.0, 1.0, 2.0])
        self.target_frame = "utm"

        self.subsample = 1

        self.marker_size = 3.0

        self.use_intensity_as_color= False
        self.color = ColorEdit(default=np.array([1.0, 1.0, 0.0]))
        self.opacity = 1.0

    def render(self, idx, view):

        ros_con = DataSource.SOURCES.connectors[1]

        msg = self.point_cloud_source.get_used_source().last_msg.msg
        pc_np = self.point_cloud_source()
        tf_mat = ros_con.get_tf_mat(msg.header.frame_id,
                                    self.target_frame,
                                    msg.header.stamp)

        if tf_mat is None:
            raise RuntimeError(f"transform from {msg.header.frame_id} to {self.target_frame} failed")

        pc = transform_point_cloud(tf_mat, pc_np)

        set_col = self.color()
        self.opacity = max(0.0, min(1.0, self.opacity))

        if self.use_intensity_as_color:
            intensity = pc_np[:]["intensity"].reshape(-1, 1)
            color = intensity.astype(float) / np.max(intensity)
            color = np.hstack((color, color, color, np.ones(color.shape))) * (*set_col, 1.0)
            color = color[::self.subsample]
        else:
            color = (*set_col, self.opacity)

        flags = viz.PlotLineFlags.NONE
        if self.no_fit:
            flags |= viz.PlotItemFlags.NO_FIT

        viz.plot(pc[::self.subsample, 0],
                 pc[::self.subsample, 1],
                 label=f"{self.label}###{idx}",
                 fmt="o",
                 marker_size=self.marker_size,
                 color=color,
                 flags=flags)
