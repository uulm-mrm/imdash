import sys
import threading

import imviz as viz

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

import tf2_ros
import ros2_numpy
import tf_transformations as tr

from dynamic_subscriber import (
        DynamicSubscriber,
        update_dynamic_subs,
        render_dynamic_subscriber,
        render_dynamic_subscriber_window
    )

from image_view import (
        ImageView,
        ImageViewSource
    )


class RosNode(Node):

    def __init__(self):

        if not rclpy.ok():
            rclpy.init()

        super().__init__("imviz_ros")

        self.multi_thread_executor = MultiThreadedExecutor()
        self.multi_thread_executor.add_node(self)

        self.ros_thread = threading.Thread(
                target=self.multi_thread_executor.spin,
                daemon=True)
        self.ros_thread.start()

        self.tf2_buffer = tf2_ros.Buffer()
        self.tf2_listener = tf2_ros.TransformListener(self.tf2_buffer, self)

    def get_tf_mat(self, from_frame, to_frame, t):
        """
        Given a tf_buffer calculates a transformation matrix
        from "from_frame" to "to_frame".
        """

        try:
            extr_trafo = self.tf2_buffer.lookup_transform(
                    to_frame, from_frame, t)
        except tf2_ros.ExtrapolationException:
            self.get_logger().error(
                    f'tf2 extrapolation error: "{from_frame}"->"{to_frame}"',
                    throttle_duration_sec=1.0)
            return None
        except tf2_ros.LookupException:
            self.get_logger().error(
                    f'tf2 lookup error: "{from_frame}"->"{to_frame}"',
                    throttle_duration_sec=1.0)
            return None

        trans_mat = tr.translation_matrix(
                ros2_numpy.numpify(extr_trafo.transform.translation))

        rot_mat = tr.quaternion_matrix(
                ros2_numpy.numpify(extr_trafo.transform.rotation))

        tf_mat = trans_mat @ rot_mat

        return tf_mat


def render_topic_tree(node, dyn_subs, views, tree_node, label="Topics"):

    if label != "":
        window_open = viz.begin_window(label)
        if not window_open:
            viz.end_window()
            return

    for k, v in tree_node.items():
        if k == "__leaf_topic_info":
            tree_open = True
            if len(tree_node) > 2:
                tree_open = viz.tree_node("topic")

            if tree_open:
                topic_name, topic_types = v

                viz.input(f"topic type", str(topic_types[0]))

                if topic_name in dyn_subs:
                    render_dynamic_subscriber(dyn_subs[topic_name])
                pubs = node.get_publishers_info_by_topic(topic_name)

                if viz.tree_node(f"publishers [{len(pubs)}]###publishers"):
                    for pub in pubs:
                        viz.text(pub.node_name)
                    viz.tree_pop()
                subs = node.get_subscriptions_info_by_topic(topic_name)
                if viz.tree_node(f"subscribers [{len(subs)}]###subscribers"):
                    for sub in subs:
                        viz.text(sub.node_name)
                    viz.tree_pop()
                        
                if len(tree_node) > 2:
                    viz.tree_pop()
        elif "__leaf_topic_info" in v:
            topic_name, topic_types = v["__leaf_topic_info"]
            has_dynamic_sub = topic_name in dyn_subs

            tree_open = viz.tree_node(
                    f"[{'x' if has_dynamic_sub else ' '}] {k}###{k}")

            if viz.begin_popup_context_item():
                if viz.menu_item("Subscribe", selected=has_dynamic_sub):
                    if not has_dynamic_sub:
                        ds = DynamicSubscriber()
                        ds.topic_type_name = topic_types[0]
                        ds.topic_name = topic_name
                        dyn_subs[topic_name] = ds
                    else:
                        ds = dyn_subs[topic_name]
                        node.destroy_subscription(ds.subscriber)
                        del dyn_subs[topic_name]

                if viz.menu_item("Create ImageView"):
                    ds = DynamicSubscriber()
                    ds.topic_type_name = topic_types[0]
                    ds.topic_name = topic_name
                    dyn_subs[topic_name] = ds

                    iv = ImageView()
                    views[id(iv)] = iv

                    ivs = ImageViewSource()
                    ivs.topic_name = ds.topic_name
                    iv.sources.append(ivs)
                viz.end_popup()

            if tree_open:
                render_topic_tree(node, dyn_subs, views, v, label="")
                viz.tree_pop()
        else:
            if viz.tree_node(k, flags=viz.TreeNodeFlags.DEFAULT_OPEN):
                render_topic_tree(node, dyn_subs, views, v, label="")
                viz.tree_pop()

    if label != "":
        viz.end_window()


def build_topic_tree(node, subs):

    topics = node.get_topic_names_and_types()
    topic_tree = {}

    for name, topic_types in topics:
        
        if name.endswith("transition_event"):
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

    for ds in subs.values():

        parts = ds.topic_name.split("/")[1:]
        cn = topic_tree

        for p in parts[:-1]:
            if p not in cn:
                cn[p] = {}
            cn = cn[p]

        if parts[-1] not in cn:
            cn[parts[-1]] = {}
            cn[parts[-1]]["__leaf_topic_info"] = (name, topic_types)

    return topic_tree


def render_views_window(views, subs):

    if viz.begin_window("Views"):

        selection = viz.combo("create", ["None", "ImageView"])
        if viz.mod():
            if selection == 1:
                nv = ImageView()
                views[id(nv)] = nv

        remove_list = []

        for v in views.values():
            viz.push_id(str(id(v)))
            tree_open = viz.tree_node(v.__class__.__name__)

            if viz.begin_popup_context_item():
                if viz.menu_item("Remove"):
                    remove_list.append(v)
                viz.end_popup()

            if tree_open:
                v.render_settings(subs)
                viz.tree_pop()

            viz.pop_id()

        for v in remove_list:
            del views[id(v)]

    viz.end_window()


class Main:

    def __init__(self):

        viz.style_colors_dark()
        viz.set_main_window_title("imviz_ros")

        self.node = RosNode()

        self.subscribers = {}
        self.views = {}

    def update(self):

        if not viz.wait(True):
            sys.exit(0)

        topic_tree = build_topic_tree(self.node, self.subscribers)

        render_topic_tree(self.node, self.subscribers, self.views, topic_tree)

        update_dynamic_subs(self.subscribers, self.node)
        render_dynamic_subscriber_window(self.subscribers)

        render_views_window(self.views, self.subscribers)

        for v in self.views.values():
            v.render(self.subscribers)
            

if __name__ == "__main__":
    viz.dev.launch(Main, "update")
