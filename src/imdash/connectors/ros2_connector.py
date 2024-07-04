import time
import queue
import threading

import numpy as np
import imviz as viz
import objtoolbox as otb

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.serialization import deserialize_message

    import tf2_ros
    import ros2_numpy
    import tf_transformations as tr

    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, PointCloud2
    from rclpy.qos import qos_profile_sensor_data

    ros2_available = True
except ImportError:
    class Node:
        pass
    ros2_available = False

from pydoc import locate

from imdash.connectors.connector_base import ConnectorBase

from imdash.utils import SelectHook


class Ros2Message:

    def __init__(self):

        self.recv_time = None
        self.stamp_time = None
        self.delay = None
        self.msg = None
        self.numpy = None


class Ros2ParameterSource:

    def __init__(self):

        self.node_name = None

        self.latest = None

        self.get_client = None
        self.set_client = None
        self.list_client = None
        self.types_client = None

    def __str__(self):

        return "[ros2 params] " + self.node_name


class Ros2TopicSource:

    def __init__(self, node):

        self.node = node

        self.subscriber = None

        self.queue = queue.deque(maxlen=1)

        self.last_msg = None

        # contains error messages, if something went wrong
        self.info_str = ""

        # check if last message was modified
        self.mod = True

        self.sub_path = []

    def cleanup(self):
        self.node.destroy_subscription(self.subscriber)

    def receive_msg(self, msg):
        self.queue.append(msg)

    @property
    def data(self):

        if self.last_msg is None:
            return None

        if self.last_msg.numpy is not None:
            return self.last_msg.numpy

        if len(self.sub_path) > 0:
            return otb.get_value_by_path(self.last_msg.msg, self.sub_path)

        return self.last_msg.msg

    def render(self):

        if self.last_msg is not None:
            viz.autogui(self.last_msg, "last_msg")


class Ros2Connector(Node, ConnectorBase):

    def __init__(self):

        self.prefix = "/ros2"

        if ros2_available:

            if not rclpy.ok():
                rclpy.init()

            super().__init__("imdash")

            self.exc = SingleThreadedExecutor()
            self.exc.add_node(self)

            self.tf2_buffer = tf2_ros.Buffer()
            self.tf2_listener = tf2_ros.TransformListener(
                self.tf2_buffer, self)

            self.create_subscription(
                    Clock,
                    "/clock",
                    self.on_clock_msg,
                    qos_profile=qos_profile_sensor_data)

            self.ros_thread = threading.Thread(
                    target=self.ros_task,
                    daemon=True)
            self.ros_thread.start()

        self.last_t = 0.0
        self.last_clock_msg = 0.0
        self.sim_clock_timeout = 2.0

        self.fixed_frame = ""

    def ros_task(self):

        try:
            self.executor.spin()
        except rclpy.executors.ExternalShutdownException:
            return

    def __savestate__(self):

        return {}

    def cleanup(self):

        if not ros2_available:
            return

        self.destroy_node()
        rclpy.shutdown()

    def on_clock_msg(self, msg):

        self.last_clock_msg = time.time()

    def get_tf_mat(self, from_frame, to_frame, t):
        """
        Given a tf_buffer calculates a transformation matrix
        from "from_frame" to "to_frame".
        """

        if not ros2_available:
            return None

        try:
            extr_trafo = self.tf2_buffer.lookup_transform(
                to_frame, from_frame, t)
        except:
            return None

        trans_mat = tr.translation_matrix(
            ros2_numpy.numpify(extr_trafo.transform.translation))

        rot_mat = tr.quaternion_matrix(
            ros2_numpy.numpify(extr_trafo.transform.rotation))

        tf_mat = trans_mat @ rot_mat

        return tf_mat

    def get_all_tf2_frames(self):

        if not ros2_available:
            return [""]

        # awful api
        tf2_frames = self.tf2_buffer.all_frames_as_string().split("\n")
        frame_names = set()
        for f in tf2_frames:
            fs = f.split(" ")
            if len(fs) != 6:
                continue
            frame_names.add(fs[1])
            frame_names.add(fs[5][:-1])

        return [""] + sorted(frame_names)

    def build_topic_tree(self):

        if not ros2_available:
            return {}

        topics = self.get_topic_names_and_types()
        topic_tree = {}

        for name, topic_types in topics:

            if name.endswith("transition_event"):
                continue

            pubs = self.get_publishers_info_by_topic(name)

            if len(pubs) == 0:
                continue

            parts = name.split("/")[1:]
            cn = topic_tree

            for p in parts[:-1]:
                if p not in cn:
                    cn[p] = {}
                cn = cn[p]

            if parts[-1] not in cn:
                cn[parts[-1]] = {}
                cn[parts[-1]]["__leaf_topic_info"] = (name, topic_types)

        return topic_tree

    def render(self, views, sources_manager):

        if viz.tree_node("ros2"):

            if not ros2_available:
                viz.text("ros2 not available", color=(1.0, 0.0, 0.0))
                viz.tree_pop()
                return

            if viz.tree_node("topics"):
                topic_tree = self.build_topic_tree()
                self.render_topic_tree(views, sources_manager, topic_tree)
                viz.tree_pop()

            viz.tree_pop()

    def render_topic_tree(self, views, sources_manager, tree_node, label="ros2 topics"):

        #tf2_frames = self.get_all_tf2_frames()
        #frame_idx = max(0, tf2_frames.index(self.fixed_frame))
        #self.fixed_frame = tf2_frames[viz.combo(
        #    "fixed_frame", tf2_frames, frame_idx)]

        for k, v in tree_node.items():
            if "__leaf_topic_info" in v:
                topic_name, _ = v["__leaf_topic_info"]
                source_path = self.prefix + "/topics" + topic_name
                tree_open = viz.tree_node(k)

                select_hook = SelectHook(sources_manager, source_path)
                select_hook.hook(None, k, None)

                # we do another tree node here so the topic is only subscribed
                # if the user actually clicked on the respective tree node
                if tree_open:
                    src = sources_manager[source_path]
                    if src is None:
                        last_msg = {}
                    elif src.last_msg is None:
                        last_msg = {}
                    else:
                        last_msg = src.last_msg.msg
                    agc = viz.AutoguiContext()
                    agc.post_header_hooks.append(select_hook.hook)
                    agc.render(last_msg)
                    viz.tree_pop()
            else:
                if viz.tree_node(k, flags=viz.TreeNodeFlags.DEFAULT_OPEN):
                    self.render_topic_tree(views, sources_manager, v, label="")
                    viz.tree_pop()

    def update_sources(self, sources_manager):

        if not ros2_available:
            return

        self._time_source.ros_time_is_active = (
                time.time() - self.last_clock_msg) < self.sim_clock_timeout

        t = self.get_clock().now().nanoseconds / 10**9
        if t < self.last_t:
            self.tf2_buffer.clear()
        self.last_t = t

        for key, s in sources_manager.items():

            if not key.startswith(self.prefix + "/topics"):
                continue

            if s is None:

                topic_name = key.replace(self.prefix + "/topics", "")
                topics = self.get_topic_names_and_types()
                try:
                    matched_topic_name, topic_type_name = [
                            (n, t[0]) for n, t in topics
                            if topic_name == n][0]
                except IndexError:
                    continue

                topic_type = locate(topic_type_name.replace("/", "."))

                s = Ros2TopicSource(self)
                s.sub_path = otb.to_path_list(topic_name.replace(matched_topic_name, "").strip())

                try:
                    s.subscriber = self.create_subscription(
                        topic_type,
                        matched_topic_name,
                        s.receive_msg,
                        qos_profile=1,
                        raw=True)
                except Exception as e:
                    print(e)
                    continue

                sources_manager[key] = s

            # pull message from queue and store for later usage

            s.mod = False

            topic_type = s.subscriber.msg_type

            try:
                ros_msg = deserialize_message(s.queue.pop(), topic_type)
            except IndexError:
                continue

            msg = Ros2Message()
            msg.msg = ros_msg
            msg.recv_time = time.time()

            if hasattr(ros_msg, "header"):
                msg.stamp_time = (ros_msg.header.stamp.sec
                                  + ros_msg.header.stamp.nanosec * 10**-9)
                msg.delay = msg.recv_time - msg.stamp_time

            if topic_type == Image:
                msg.numpy = ros2_numpy.numpify(ros_msg)
            if topic_type == PointCloud2:
                msg.numpy = ros2_numpy.numpify(ros_msg)

            s.last_msg = msg
            s.mod = True
