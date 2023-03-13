import signal
import datetime

import os
import re
import os.path as osp

import multiprocessing as mp

import imviz as viz

from imdash.utils import ViewBase, DataSource
from imdash.connectors import Ros2Connector
from imdash.connectors import ros2_connector


if ros2_connector.ros2_available:

    from launch import LaunchService, LaunchDescription
    from launch.actions import GroupAction, ExecuteProcess
    from launch_ros.actions import PushRosNamespace, Node

    def generate_launch_description(record_path,
                                    record_name_format,
                                    remap_namespace,
                                    record_topics,
                                    record_relay_topics):
        args = []
        record_relay_nodes = []

        for topic in record_relay_topics:
            if topic[0] == "/":
                rel_topic = topic[1:]
            else:
                rel_topic = topic
            node_name = rel_topic.replace("/", "_")
            record_relay_nodes.append(
                Node(
                    package='topic_tools',
                    executable='relay',
                    name=f'relay_{node_name}',
                    parameters = [{
                        'input_topic': topic,
                        'output_topic': rel_topic
                    }],
                )
            )
            record_topics.append(osp.join('/', remap_namespace, rel_topic))

        args.append(
            GroupAction(
                actions=[PushRosNamespace(remap_namespace)] + record_relay_nodes,
            )
        )

        record_name = datetime.datetime.now().strftime(record_name_format)
        record_path = osp.join(record_path, record_name)

        record_launch_desc = LaunchDescription([
            ExecuteProcess(
                cmd=['ros2', 'bag', 'record',
                     '--storage', 'sqlite3',
                     '-o', str(record_path),
                     *record_topics],
                output='screen'
            )
        ])

        launch_desc = [record_launch_desc]

        return LaunchDescription([
                *args,
                *launch_desc
            ])


class RosBagRecordView(ViewBase):

    def __init__(self):

        super().__init__()

        self.title = "ROS2 Bag Recorder"
        self.remap_namespace = "rec"

        self.topic_filter = ""

        self.record_path = osp.expanduser("~")
        self.record_name_format = "rosbag2_%Y_%m_%d-%H_%M_%S"
        self.record_topics = set()
        self.record_and_remap_topics = set()

        self.launch_service = None
        self.launch_proc = None

        self.filter_selected = False

    def __autogui__(self, name, ctx, **kwargs):

        self.title = ctx.render(self.title, "title")
        self.remap_namespace = ctx.render(
                self.remap_namespace, "remap namespace")

        self.record_path = viz.file_dialog_popup(
                "Select record path", self.record_path)

        if viz.button("..."):
            viz.open_popup("Select record path")
        viz.same_line()
        self.record_path = viz.input("path", self.record_path)
        self.record_name_format = viz.input(
                "name format", self.record_name_format)

    def __savestate__(self):

        s = self.__dict__.copy()
        s["record_topics"] = list(self.record_topics)
        s["record_and_remap_topics"] = list(self.record_and_remap_topics)
        del s["launch_service"]
        del s["launch_proc"]
        del s["topic_filter"]
        del s["filter_selected"]

        return s

    def get_topics(self, ros_con):

        topics = ros_con.get_topic_names_and_types()
        topic_names = [t[0] for t in topics]

        if not type(self.record_topics) == set:
            self.record_topics = set(self.record_topics)
        if not type(self.record_and_remap_topics) == set:
            self.record_and_remap_topics = set(self.record_and_remap_topics)

        all_topics = self.record_topics.union(self.record_and_remap_topics)
        if not self.filter_selected:
            all_topics = set(topic_names).union(all_topics)
        all_topics = list(all_topics)
        all_topics.sort()
        if len(self.topic_filter) > 0:
            try:
                all_topics = [t for t in all_topics
                              if re.search(self.topic_filter, t)]
            except re.error:
                pass

        return all_topics

    def render_toolbar(self, topics):

        if self.launch_service is None:
            if viz.button("Start recording"):
                os.makedirs(self.record_path, exist_ok=True)
                desc = generate_launch_description(
                        self.record_path,
                        self.record_name_format,
                        self.remap_namespace,
                        list(self.record_topics),
                        list(self.record_and_remap_topics))
                self.launch_service = LaunchService()
                self.launch_service.include_launch_description(desc)
                self.launch_proc = mp.Process(target=self.launch_service.run)
                self.launch_proc.start()
        else:
            if viz.button("Stop recording"):
                os.kill(self.launch_proc.pid, signal.SIGINT)
                self.launch_service = None
                self.launch_proc = None
        viz.same_line()
        viz.text(f"{len(self.record_topics)} topics "
                 + f"and {len(self.record_and_remap_topics)} remapped topics")
        viz.separator()

        if viz.button("Record all"):
            self.record_topics = self.record_topics.union(topics)
        viz.same_line()
        if viz.button("Remap all"):
            self.record_and_remap_topics = self.record_and_remap_topics.union(topics)
        viz.same_line()
        if viz.button("Record none"):
            self.record_topics = set()
            self.record_and_remap_topics = set()
        viz.same_line()
        if viz.button("Remap none"):
            self.record_and_remap_topics = set()

        self.topic_filter = viz.input("search", self.topic_filter)
        viz.same_line()
        self.filter_selected = viz.checkbox(
                "hide unselected", self.filter_selected)

    def render_topic_table(self, topics):

        table_flags = (viz.TableFlags.PAD_OUTER_X
                    | viz.TableFlags.SCROLL_Y
                    | viz.TableFlags.BORDERS_OUTER
                    | viz.TableFlags.BORDERS_INNER_V)

        if viz.begin_table("table", 3, flags=table_flags):
            viz.table_setup_column("Topic", viz.TableColumnFlags.WIDTH_STRETCH)
            viz.table_setup_column("Record", viz.TableColumnFlags.WIDTH_FIXED, 50.0)
            viz.table_setup_column("Remap", viz.TableColumnFlags.WIDTH_FIXED, 50.0)
            viz.table_setup_scroll_freeze(0, 1)
            viz.table_headers_row()
            for topic_name in topics:
                viz.table_next_column()
                viz.text(topic_name)
                viz.table_next_column()
                sel = viz.checkbox(f"###rec_{topic_name}",
                                   topic_name in self.record_topics
                                   or topic_name in self.record_and_remap_topics)
                if viz.mod():
                    if sel:
                        self.record_topics.add(topic_name)
                    else:
                        if topic_name in self.record_topics:
                            self.record_topics.remove(topic_name)
                        if topic_name in self.record_and_remap_topics:
                            self.record_and_remap_topics.remove(topic_name)

                viz.table_next_column()
                sel = viz.checkbox(f"###rec_and_remap_{topic_name}",
                                   topic_name in self.record_and_remap_topics)
                if viz.mod():
                    if sel:
                        if topic_name in self.record_topics:
                            self.record_topics.remove(topic_name)
                        self.record_and_remap_topics.add(topic_name)
                    else:
                        self.record_and_remap_topics.remove(topic_name)
                viz.table_next_row()
            viz.end_table()

    def render(self, sources):

        if not self.show:
            return

        window_open = viz.begin_window(f"{self.title}###{self.uuid}")
        self.show = viz.get_window_open()

        if viz.begin_popup_context_item():
            if viz.begin_menu("Edit"):
                viz.autogui(self, "", sources=sources)
                viz.end_menu()
            if viz.menu_item("Delete"):
                self.destroyed = True
            viz.end_popup()

        if window_open:
            ros_cons = [s for s in sources.connectors
                        if type(s) == Ros2Connector]
            if len(ros_cons) == 0 or ros2_connector.ros2_available == False:
                viz.text("ROS2 not available!", color="red")
            else:
                topics = self.get_topics(ros_cons[0])
                self.render_toolbar(topics)
                self.render_topic_table(topics)
        viz.end_window()
