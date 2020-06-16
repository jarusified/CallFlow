# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# ------------------------------------------------------------------------------
# Library imports
import math
import pandas as pd
import networkx as nx

# ------------------------------------------------------------------------------
# CallFlow imports
import callflow
from callflow.timer import Timer
from callflow import SuperGraph

LOGGER = callflow.get_logger(__name__)

# ------------------------------------------------------------------------------
# Single Super Graph class.
class SingleSankey:

    _COLUMNS = ["actual_time", "time (inc)", "module", "name", "time", "type", "module"]

    def __init__(self, supergraph={}, path="path"):
        assert isinstance(supergraph, SuperGraph)
        assert isinstance(path, str)
        assert path in ["path", "group_path", "component_path"]

        # Set the current graph being rendered.
        self.supergraph = supergraph
        self.path = path

        self.timer = Timer()

        LOGGER.info("Creating the Single sankey for {0}.".format(self.supergraph.tag))

        with self.timer.phase("Construct Graph"):
            self.nxg = SingleSankey.create_nxg_from_paths(self.supergraph.gf.df, self.path)

        with self.timer.phase("Add graph attributes"):
            self._add_node_attributes()
            self._add_edge_attributes()

        LOGGER.debug(self.timer)

    @staticmethod
    def create_nxg_from_paths(df, path):
        assert isinstance(df, pd.DataFrame)
        assert path in df.columns

        module_name_group_df = df.groupby(["module", "name"])

        nxg = nx.DiGraph()
        cct = nx.DiGraph()

        paths_df = df.groupby(["name", path])

        for (callsite, path), path_df in paths_df:
            path_list = SingleSankey.remove_cycles_in_paths(path)
            for callsite_idx, callsite in enumerate(path_list):
                if callsite_idx != len(path_list) - 1:
                    source = path_list[callsite_idx]
                    target = path_list[callsite_idx + 1]

                    source_module = source["module"]
                    target_module = target["module"]

                    source_callsite = source["callsite"]
                    target_callsite = target["callsite"]

                    source_df = module_name_group_df.get_group((source_module, source_callsite))
                    target_df = module_name_group_df.get_group((target_module, target_callsite))

                    has_caller_edge = nxg.has_edge(
                        source_module, target_module
                    )
                    has_callback_edge = nxg.has_edge(
                        target_module, source_module
                    )
                    has_cct_edge = cct.has_edge(source_callsite, target_callsite)

                    source_weight = source_df["time (inc)"].max()
                    target_weight = target_df["time (inc)"].max()

                    source_dataset = source_df["dataset"].unique().tolist()
                    target_dataset = target_df["dataset"].unique().tolist()

                    if has_callback_edge:
                        edge_type = "callback"
                        weight = 0
                    else:
                        edge_type = "caller"

                    edge_dict = {
                        "source_callsite": source_callsite,
                        "target_callsite": target_callsite,
                        "edge_type": edge_type,
                        "weight": target_weight,
                        "source_dataset": source_dataset,
                        "target_dataset": target_dataset,
                    }

                    node_dict = {"type": "super-node"}

                    # If the module-module edge does not exist.
                    if (
                        not has_caller_edge
                        and not has_cct_edge
                        and not has_callback_edge
                    ):
                        print(
                            f"Add {edge_type} edge for : {source_module}--{target_module}"
                        )
                        nxg.add_node(source_module, attr_dict=node_dict)
                        nxg.add_node(target_module, attr_dict=node_dict)
                        nxg.add_edge(source_module, target_module, attr_dict=[edge_dict])

                    elif not has_cct_edge and not has_callback_edge:
                        # print(f"Edge already exists for : {source_module}--{target_module}")
                        edge_data = nxg.get_edge_data(*(source_module, target_module))
                        nxg[source_module][target_module]["attr_dict"].append(edge_dict)

                    if not has_cct_edge:
                        cct.add_edge(
                            source_callsite,
                            target_callsite,
                            attr_dict={"weight": target_weight},
                        )

        return nxg

    @staticmethod
    def remove_cycles_in_paths(path):

        from ast import literal_eval as make_tuple

        ret = []
        moduleMapper = {}
        dataMap = {}

        if isinstance(path, float):
            return []
        path = make_tuple(path)
        for idx, elem in enumerate(path):
            callsite = elem.split("=")[1]
            module = elem.split("=")[0]
            if module not in dataMap:
                moduleMapper[module] = 0
                dataMap[module] = [
                    {"callsite": callsite, "module": module, "level": idx}
                ]
            else:
                flag = [p["level"] == idx for p in dataMap[module]]
                if np.any(np.array(flag)):
                    moduleMapper[module] += 1
                    dataMap[module].append(
                        {
                            "callsite": callsite,
                            "module": module + "=" + callsite,
                            "level": idx,
                        }
                    )
                else:
                    dataMap[module].append(
                        {"callsite": callsite, "module": module, "level": idx}
                    )
            ret.append(dataMap[module][-1])

        return ret

    @staticmethod
    def module_time(group_df, module_callsite_map, module):
        exc_time_sum = 0
        inc_time_max = 0
        for callsite in module_callsite_map[module]:
            callsite_df = group_df.get_group((module, callsite))
            max_inc_time = callsite_df["time (inc)"].max()
            inc_time_max = max(inc_time_max, max_inc_time)
            max_exc_time = callsite_df["time"].max()
            exc_time_sum += max_exc_time
        return {"Inclusive": inc_time_max, "Exclusive": exc_time_sum}

    @staticmethod
    def callsite_time(group_df, module, callsite):
        callsite_df = group_df.get_group((module, callsite))
        max_inc_time = callsite_df["time (inc)"].max()
        max_exc_time = callsite_df["time"].max()

        return {"Inclusive": max_inc_time, "Exclusive": max_exc_time}

    @staticmethod
    def ensemble_map(df, nxg, columns=[]):
        assert isinstance(df, pd.DataFrame)
        assert isinstance(nxg, nx.DiGraph)
        ret = {}

        module_group_df = df.groupby(["module"])
        module_name_group_df = df.groupby(["module", "name"])

        module_callsite_map = module_group_df["name"].unique().to_dict()

        module_time_inc_map = module_group_df["time (inc)"].max().to_dict()
        module_time_exc_map = module_group_df["time"].max().to_dict()

        name_time_inc_map = module_name_group_df["time (inc)"].max().to_dict()
        name_time_exc_map = module_name_group_df["time"].max().to_dict()

        # loop through the nodes
        for node in nxg.nodes(data=True):
            node_name = node[0]
            node_dict = node[1]["attr_dict"]

            if node_dict["type"] == "component-node":
                module = node_name.split("=")[0]
                callsite = node_name.split("=")[1]
                actual_time = SuperGraph.callsite_time(group_df=module_name_group_df, module=module, callsite=callsite)
                time_inc = name_time_inc_map[(module, callsite)]
                time_exc = name_time_exc_map[(module, callsite)]

            elif node_dict["type"] == "super-node":
                module = node_name
                callsite = module_callsite_map[module].tolist()
                actual_time = SuperGraph.module_time(group_df=module_name_group_df, module_callsite_map=module_callsite_map, module=module)

                time_inc = module_time_inc_map[module]
                time_exc = module_time_exc_map[module]

            for column in columns:
                if column not in ret:
                    ret[column] = {}

                if column == "time (inc)":
                    ret[column][node_name] = time_inc

                elif column == "time":
                    ret[column][node_name] = time_exc

                elif column == "actual_time":
                    ret[column][node_name] = actual_time

                elif column == "module":
                    ret[column][node_name] = module

                elif column == "name":
                    ret[column][node_name] = callsite

                elif column == "type":
                    ret[column][node_name] = node_dict["type"]

        return ret

    @staticmethod
    def dataset_map(df=pd.DataFrame([]), nxg=nx.DiGraph(), columns=[], tag=""):
        ret = {}

        # Reduce the entire_df to respective target dfs.
        target_df = df.loc[df["dataset"] == tag]

        # Unique modules in the target run
        target_modules = target_df["module"].unique()

         # Group the dataframe in two ways.
        # 1. by module
        # 2. by module and callsite
        target_module_group_df = target_df.groupby(["module"])
        target_module_name_group_df = target_df.groupby(["module", "name"])

        # Module map for target run {'module': [Array of callsites]}
        target_module_callsite_map = target_module_group_df["name"].unique().to_dict()

        # Inclusive time maps for the module level and callsite level.
        target_module_time_inc_map = target_module_group_df["time (inc)"].max().to_dict()
        target_name_time_inc_map = target_module_name_group_df["time (inc)"].max().to_dict()

        # Exclusive time maps for the module level and callsite level.
        target_module_time_exc_map = target_module_group_df["time"].max().to_dict()
        target_name_time_exc_map = target_module_name_group_df["time"].max().to_dict()

        for node in nxg.nodes(data=True):
            node_name = node[0]
            node_dict = node[1]["attr_dict"]
            if node_name in target_module_callsite_map.keys():
                if node_dict["type"] == "component-node":
                    module = node_name.split("=")[0]
                    callsite = node_name.split("=")[1]
                    actual_time = SuperGraph.callsite_time(group_df=target_module_group_df,module=module, callsite=callsite)
                    time_inc = target_name_time_inc_map[(module, callsite)]
                    time_exc = target_name_time_exc_map[(module, callsite)]

                elif node_dict["type"] == "super-node":
                    module = node_name
                    callsite = target_module_callsite_map[module].tolist()
                    actual_time = SuperGraph.module_time(group_df=target_module_name_group_df,module_callsite_map=target_module_callsite_map, module=module)

                    time_inc = target_module_time_inc_map[module]
                    time_exc = target_module_time_exc_map[module]

                if node_name not in ret:
                    ret[node_name] = {}

                for column in columns:
                    if column == "time (inc)":
                        ret[node_name][column] = time_inc

                    elif column == "time":
                        ret[node_name][column] = time_exc

                    elif column == "module":
                        ret[node_name][column] = module

                    elif column == "actual_time":
                        ret[node_name][column] = actual_time

                    elif column == "name":
                        ret[node_name][column] = callsite

                    elif column == "type":
                        ret[node_name][column] = node_dict["type"]

        return ret

    # --------------------------------------------------------------------------
    def _add_node_attributes(self):
        ensemble_mapping = SuperGraph.ensemble_map(df=self.supergraph.gf.df, nxg=self.nxg, columns=SingleSankey._COLUMNS)
        for idx, key in enumerate(ensemble_mapping):
            nx.set_node_attributes(self.nxg, name=key, values=ensemble_mapping[key])

        dataset_mapping = SuperGraph.dataset_map(df=self.supergraph.gf.df, nxg=self.nxg, tag=self.supergraph.tag, columns=SingleSankey._COLUMNS)
        nx.set_node_attributes(self.nxg, name=self.supergraph.tag, values=dataset_mapping)

    def _add_edge_attributes(self):
        inclusive_flow = SuperGraph.flows(self.nxg)
        nx.set_edge_attributes(self.nxg, name="weight", values=inclusive_flow)
        # exc_capacity_mapping = self.calculate_exc_weight(self.g)
        # nx.set_edge_attributes(self.g, name="exc_weight", values=exc_capacity_mapping)

    def remove_calculate_exc_weight(self, graph):
        ret = {}
        additional_flow = {}
        for edge in graph.edges(data=True):
            source_module = edge[0]
            target_module = edge[1]
            source_name = edge[2]["attr_dict"]["source_callsite"]
            target_name = edge[2]["attr_dict"]["target_callsite"]

            source_exc = self.df.loc[(self.df["name"] == source_name)]["time"].max()
            target_exc = self.df.loc[(self.df["name"] == target_name)]["time"].max()

            if source_exc == target_exc:
                ret[(edge[0], edge[1])] = source_exc
            else:
                ret[(edge[0], edge[1])] = target_exc

        return ret

    @staticmethod
    def remove_calculate_flows(graph):
        """
        Calculate the sankey flows from source node to target node.
        """
        ret = {}
        for edge in graph.edges(data=True):
            source_module = edge[0]
            target_module = edge[1]
            source_name = edge[2]["attr_dict"]["source_callsite"]
            target_name = edge[2]["attr_dict"]["target_callsite"]

            source_inc = self.df.loc[(self.df["name"] == source_name)][
                "time (inc)"
            ].max()
            target_inc = self.df.loc[(self.df["name"] == target_name)][
                "time (inc)"
            ].max()

            ret[(edge[0], edge[1])] = target_inc

        return ret

    @staticmethod
    def flows(nxg):
        flow_mapping = {}
        for edge in nxg.edges(data=True):
            if (edge[0], edge[1]) not in flow_mapping:
                flow_mapping[(edge[0], edge[1])] = 0

            attr_dict = edge[2]["attr_dict"]
            for d in attr_dict:
                flow_mapping[(edge[0], edge[1])] += d["weight"]

        ret = {}
        for edge in nxg.edges(data=True):
            edge_tuple = (edge[0], edge[1])
            if edge_tuple not in flow_mapping:
                # Check if it s a reveal edge
                attr_dict = edge[2]["attr_dict"]
                if attr_dict["edge_type"] == "reveal_edge":
                    flow_mapping[edge_tuple] = attr_dict["weight"]
                    ret[edge_tuple] = flow_mapping[edge_tuple]
                else:
                    ret[edge_tuple] = 0
            else:
                ret[edge_tuple] = flow_mapping[edge_tuple]

        return ret

    def remove_dataset_map(self, nodes, dataset):
        ret = {}
        for node in self.g.nodes():
            if "=" in node:
                node_name = node.split("=")[1]
            else:
                node_name = node

            if node not in ret:
                ret[node] = {}

            node_df = self.df.loc[
                (self.df["module"] == node_name) & (self.df["dataset"] == dataset)
            ]

            for column in self.columns:
                column_data = node_df[column]

                if (
                    column == "time (inc)"
                    or column == "time"
                    or column == "component_level"
                ):
                    if len(column_data.value_counts()) > 0:
                        ret[node][column] = column_data.max()
                    else:
                        ret[node][column] = -1

                elif column == "callers" or column == "callees":
                    if len(column_data.value_counts()) > 0:
                        ret[node][column] = make_tuple(column_data.tolist()[0])

                elif column == "component_path" or column == "group_path":

                    if len(column_data.value_counts() > 0):
                        ret[node][column] = list(make_tuple(column_data.tolist()[0]))
                    else:
                        ret[node][column] = []
        return ret
