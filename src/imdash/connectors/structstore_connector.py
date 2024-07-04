import os
import copy
import imviz as viz
import numpy as np

from contextlib import contextmanager

import objtoolbox as otb

try:
    import structstore as sts
    structstore_available = True
except ImportError:
    structstore_available = False

from imdash.connectors.connector_base import ConnectorBase

from imdash.utils import SelectHook


@contextmanager
def locked_path(obj, path):

    with obj.lock():

        locks = []
        sub = obj

        for p in path:
            res = None
            if type(p) == str:
                res = getattr(sub, p, None)
            if res is None:
                try:
                    res = sub[p]
                except (TypeError, KeyError):
                    raise RuntimeError(f"attribute \"{'.'.join(path)}\" not found")

            try:
                l = res.lock()
                l.__enter__()
                locks.append(l)
            except AttributeError:
                pass

            sub = res

        try:
            yield sub
        finally:
            for l in locks[::-1]:
                l.__exit__(None, None, None)


class StructStoreSource:

    def __init__(self):

        self.shm_path = None
        self.sub_path = None
        self.store = None

    @property
    def data(self):
        with locked_path(self.store, self.sub_path) as res:
            return copy.deepcopy(res)

    @data.setter
    def data(self, val):
        with locked_path(self.store, self.sub_path[:-1]) as res:
            otb.set_value_by_path(res, self.sub_path[-1:], val)

    def __autogui__(self, name, ctx, **kwargs):

        with self.store.lock():
            res = ctx.render(self.store, name, **kwargs)
        return res


class StructStoreConnector(ConnectorBase):

    def __init__(self):

        super().__init__("/structstores")

        self.stores = {}

    def cleanup(self):

        for v in self.stores.values():
            v.close()
        self.stores = {}

    def render(self, views, sources_manager):

        if viz.tree_node("structstores"):

            if not structstore_available:
                viz.text("struct stores not available", color=(1.0, 0.0, 0.0))
            else:
                self.show_structstore_view = viz.get_window_open()

                select_hook = SelectHook(sources_manager, "")

                agc = viz.AutoguiContext()
                agc.post_header_hooks.append(select_hook.hook)

                for shm_path in os.listdir("/dev/shm"):

                    source_path = self.prefix + "/" + shm_path
                    select_hook.base_path = source_path

                    tree_open = viz.tree_node(shm_path)

                    select_hook.hook(None, shm_path, agc)

                    # we do another tree node here so the structstore is only opened
                    # if the user actually clicked on the respective tree node
                    if tree_open:
                        src = sources_manager[source_path]
                        if src is None:
                            src = {}
                        agc.render(src)
                        viz.tree_pop()

            viz.tree_pop()

    def update_sources(self, sources):
        
        if not structstore_available:
            return

        used_stores = {}

        for key, s in sources.items():

            if not key.startswith(self.prefix):
                continue

            if s is None:
                s = StructStoreSource()
                path = key.replace(self.prefix, "")
                path_split = path.split("/", 2)[1:]

                try:
                    s.shm_path = path_split[0].strip()
                    if len(path_split) > 1:
                        s.sub_path = otb.to_path_list(path_split[1].strip())
                    else:
                        s.sub_path = []

                    # try to get store from store cache otherwise open it
                    try:
                        s.store = self.stores[s.shm_path]
                    except KeyError:
                        s.store = sts.StructStoreShared(s.shm_path)
                        self.stores[s.shm_path] = s.store

                    sources[key] = s
                except RuntimeError as e:
                    continue

            try:
                s.store.revalidate()
            except RuntimeError:
                continue

            # only keep used stores
            used_stores[s.shm_path] = self.stores[s.shm_path]

        # ensure that unneeded stores are immediately deinitialized
        for k, v in self.stores.items():
            if not k in used_stores:
                v.close()

        self.stores = used_stores
