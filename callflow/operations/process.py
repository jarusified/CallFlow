##############################################################################
# Copyright (c) 2018-2019, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Callflowt.
# Created by Suraj Kesavan <kesavan1@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# For details, see: https://github.com/LLNL/Callflow
# Please also read the LICENSE file for the MIT License notice.
##############################################################################
import bisect
import random
from functools import wraps

import numpy as np
from scipy.stats import kurtosis, skew

import callflow

LOGGER = callflow.get_logger(__name__)


class Process:
    """
    Preprocess the dataframe
    Builder object
    Preprocess.add_X().add_Y().....
    """

    def __init__(self, gf, tag):
        self.gf = gf
        self.tag = tag

    class Builder(object):
        def __init__(self, gf, tag):
            self.callers = {}
            self.callees = {}
            self.frames = {}
            self.paths = {}
            self.hatchet_nodes = {}

            self.gf = gf
            self.df = gf.df
            self.graph = gf.graph
            self.tag = tag

            # Logger Information
            self.cct_nodes = []
            self.callgraph_nodes = []
            self.supergraph_nodes = []
            self.unmapped_targets = []

            self.callgraph_nodes_np = np.array([])
            self.cct_nodes_np = np.array([])
            self.graphMapper()
            self.map = {}

        def convertFrameList(self, nodes):
            ret = []
            for node in nodes:
                ret.append(node.frame.get("name"))
            return ret

        def graphMapper(self):
            graph = self.graph

            for node in graph.traverse():
                node_dict = callflow.utils.node_dict_from_frame(node.frame)

                if node_dict["type"] == "loop":
                    node_name = "Loop@" + callflow.utils.sanitize_name(
                        node_dict["name"] + ":" + str(node_dict["line"])
                    )
                elif node_dict["type"] == "statement":
                    node_name = (
                        callflow.utils.sanitize_name(node_dict["name"])
                        + ":"
                        + str(node_dict["line"])
                    )
                else:
                    node_name = node_dict["name"]

                node_paths = node.paths()
                self.paths[node_name] = node_paths
                self.callers[node_name] = self.convertFrameList(node.parents)
                self.callees[node_name] = self.convertFrameList(node.children)
                self.hatchet_nodes[node_name] = node

        def build(self):
            return Process(self.gf, self.tag)

        # Add the path information from the node object
        def add_path(self):
            self.raiseExceptionIfNodeCountNotEqual(self.paths)
            self.df["path"] = self.df["name"].apply(
                lambda node_name: callflow.utils.path_list_from_frames(
                    self.paths[node_name]
                )
            )
            return self

        # Imbalance percentage Series in the dataframe
        def add_imbalance_perc(self):
            inclusive = {}
            exclusive = {}
            std_deviation_inclusive = {}
            std_deviation_exclusive = {}

            skewness_inclusive = {}
            skewness_exclusive = {}

            kurtosis_inclusive = {}
            kurtosis_exclusive = {}

            for node_name in self.df["name"].unique():
                node_df = self.df.loc[self.df["name"] == node_name]

                max_incTime = node_df["time"].mean()
                mean_incTime = node_df["time (inc)"].mean()

                max_excTime = node_df["time"].max()
                mean_excTime = node_df["time"].mean()

                if mean_incTime == 0.0:
                    mean_incTime = 1.0

                inclusive[node_name] = (max_incTime - mean_incTime) / mean_incTime
                exclusive[node_name] = (max_excTime - mean_excTime) / mean_excTime

                std_deviation_inclusive[node_name] = np.std(
                    node_df["time (inc)"].tolist(), ddof=1
                )
                std_deviation_exclusive[node_name] = np.std(
                    node_df["time"].tolist(), ddof=1
                )

                skewness_inclusive[node_name] = skew(node_df["time (inc)"].tolist())
                skewness_exclusive[node_name] = skew(node_df["time"].tolist())

                kurtosis_inclusive[node_name] = kurtosis(node_df["time (inc)"].tolist())
                kurtosis_exclusive[node_name] = kurtosis(node_df["time"].tolist())

            self.df["imbalance_perc_inclusive"] = self.df["name"].apply(
                lambda name: inclusive[name]
            )
            self.df["imbalance_perc_exclusive"] = self.df["name"].apply(
                lambda name: exclusive[name]
            )

            self.df["std_deviation_inclusive"] = self.df["name"].apply(
                lambda name: std_deviation_inclusive[name]
            )
            self.df["std_deviation_exclusive"] = self.df["name"].apply(
                lambda name: std_deviation_exclusive[name]
            )

            self.df["skewness_inclusive"] = self.df["name"].apply(
                lambda name: skewness_inclusive[name]
            )
            self.df["skewness_exclusive"] = self.df["name"].apply(
                lambda name: skewness_exclusive[name]
            )

            self.df["kurtosis_inclusive"] = self.df["name"].apply(
                lambda name: kurtosis_inclusive[name]
            )
            self.df["kurtosis_exclusive"] = self.df["name"].apply(
                lambda name: kurtosis_exclusive[name]
            )

            return self

        def add_callers_and_callees(self):
            self.df["callees"] = self.df["name"].apply(lambda node: self.callees[node])
            self.df["callers"] = self.df["name"].apply(lambda node: self.callers[node])

            return self

        # node_name is different from name in dataframe. So creating a copy of it.
        def add_vis_node_name(self):
            self.module_group_df = self.df.groupby(["module"])
            self.module_callsite_map = self.module_group_df["name"].unique()

            self.name_group_df = self.df.groupby(["name"])
            self.callsite_module_map = self.name_group_df["module"].unique().to_dict()

            self.df["vis_node_name"] = self.df["name"].apply(
                lambda name: callflow.utils.sanitize_name(
                    self.callsite_module_map[name][0]
                )
                + "="
                + name
            )
            return self

        def add_node_name_hpctoolkit(self, node_name_map):
            self.df["node_name"] = self.df["name"].apply(
                lambda name: node_name_map[name]
            )
            return self

        def add_module_name_hpctoolkit(self):
            self.df["module"] = self.df["module"].apply(lambda name: callflow.utils.sanitize_name(name))
            return self

        def add_node_name_caliper(self, node_module_map):
            self.df["node_name"] = self.df["name"].apply(
                lambda name: name_module_map[name]
            )

        def add_module_name_caliper(self, module_map):
            self.df["module"] = self.df["name"].apply(lambda name: module_map[name])
            return self

        def add_dataset_name(self):
            self.df["dataset"] = self.tag
            return self

        def add_rank_column(self):
            if "rank" not in self.df.columns:
                self.df["rank"] = 0
            return self

        def add_time_columns(self):
            if "time (inc)" not in self.df.columns:
                self.df["time (inc)"] = self.df["inclusive#time.duration"]

            if "time" not in self.df.columns:
                self.df["time"] = self.df["sum#time.duration"]
            return self

        def create_name_module_map(self):
            self.name_module_map = (
                self.df.groupby(["name"])["module"].unique().to_dict()
            )
            return self

        def raiseExceptionIfNodeCountNotEqual(self, attr):
            map_node_count = len(attr.keys())
            df_node_count = len(self.df["name"].unique())
            LOGGER.debug(
                f"[Validation] Map contains: {map_node_count} callsites, graph contains: {df_node_count} callsites"
            )
            if map_node_count != df_node_count:
                raise Exception(
                    f"Unmatched Preprocessing maps: Map contains: {map_node_count} nodes, graph contains: {df_node_count} nodes"
                )

        def logInformation(self):
            LOGGER.info(f"CCT node count : {len(self.cct_nodes)}")
            LOGGER.info(f"CallGraph node count: {len(self.callgraph_nodes)}")
            LOGGER.info(f"SuperGraph node count: {len(self.df['module'].unique())}")
            return self
