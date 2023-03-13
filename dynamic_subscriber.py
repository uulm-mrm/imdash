import time
import queue
import numpy as np
import imviz as viz

from pydoc import locate

from rclpy.serialization import deserialize_message


class DynamicSubscriber:

    def __init__(self):

        # these are included here to make saving work
        self.topic_name = None
        self.topic_type_name = None

        self.topic_type = None
        self.subscriber = None

        self.queue = queue.deque(maxlen=1)

        self.latest_msg = None 
        self.latest_msg_recv_wall_time = 0.0

        self.hz_window = 100
        self.hz_queue = queue.deque(maxlen=self.hz_window)

        # contains error messages, if something went wrong
        self.info_str = ""

    def receive_msg(self, msg):

        now = time.time()
        dt = now - self.latest_msg_recv_wall_time

        if self.hz_queue.maxlen != self.hz_window:
            self.hz_queue = queue.deque(maxlen=self.hz_window)

        self.hz_queue.append(1.0 / dt)

        self.latest_msg_recv_wall_time = now

        self.queue.append(msg)

    def __getstate__(self):

        d = { 
            "topic_name": topic_name,
            "topic_type_name": topic_type_name,
            "hz_window": hz_window
        }

        return d


def update_dynamic_subs(subs, node):

    for ds in subs.values():

        # update subscription

        if ds.subscriber is None:
            try:
                ds.topic_type = locate(ds.topic_type_name.replace("/", "."))
                ds.subscriber = node.create_subscription(
                        ds.topic_type,
                        ds.topic_name,
                        ds.receive_msg,
                        qos_profile=1,
                        raw=True)
            except Exception as e:
                ds.info_str = str(e)
        else:
            if ds.topic_name != ds.subscriber.topic_name:
                node.destroy_subscription(ds.subscriber)
                ds.subscriber = None

        # pull message from queue and store for later usage

        try:
            ds.latest_msg = deserialize_message(ds.queue.pop(), ds.topic_type)
        except IndexError:
            pass


def render_dynamic_subscriber(ds):

    viz.drag(f"recv. wall time", ds.latest_msg_recv_wall_time)

    if ds.latest_msg is not None:
        viz.autogui(ds.latest_msg, f"latest_msg###latest_msg")

    hz_list = list(ds.hz_queue)
    if len(hz_list) > 0:
        hz_mean = round(np.mean(hz_list), 2)
        if viz.tree_node(f"Hz mean: {hz_mean}###Rate"):
            ds.hz_window = viz.drag("hz window", ds.hz_window)
            viz.drag("hz std", round(np.std(hz_list), 2))
            viz.drag("hz min", round(np.min(hz_list), 2))
            viz.drag("hz max", round(np.max(hz_list), 2))
            viz.tree_pop()


def render_dynamic_subscriber_window(subs):

    if viz.begin_window("Subscriptions"):

        for topic, ds in subs.items():
            if viz.tree_node(topic):
                render_dynamic_subscriber(ds)
                viz.tree_pop()

    viz.end_window()
