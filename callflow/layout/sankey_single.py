# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# ------------------------------------------------------------------------------
# Library imports
import math
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

    _COLUMNS = ["time (inc)", "module", "name", "time", "type", "module", "actual_time"]

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
            self.nxg = SuperGraph._create_nxg_from_paths(
                self.supergraph.gf.df[self.path].unique().tolist()
            )

        with self.timer.phase("Add graph attributes"):
            self._add_node_attributes()
            self._add_edge_attributes()

        LOGGER.debug(self.timer)

    # --------------------------------------------------------------------------
    def _add_node_attributes(self):

        # ----------------------------------------------------------------------
        # compute data map
        datamap = {}
        for callsite in self.nxg.nodes():
            if callsite not in datamap:
                datamap[callsite] = {}

            for column in SingleSankey._COLUMNS:
                if column not in datamap:
                    datamap[column] = {}

                if column == "time (inc)":
                    datamap[column][callsite] = self.supergraph.module_time_inc_map
                elif column == "time":
                    datamap[column][callsite] = self.supergraph.module_time_exc_map
                # elif column == "callers" or column == "callees":

                # elif column == "component_path" or column == "group_path":

        for idx, key in enumerate(datamap):
            nx.set_node_attributes(self.nxg, name=key, values=datamap[key])

    def _add_edge_attributes(self):

        inclusive_flow = {}
        for edge in self.nxg.edges(data=True):
            source_module = edge[0]
            target_module = edge[1]
            source_name = edge[2]["attr_dict"]["source_callsite"]
            target_name = edge[2]["attr_dict"]["target_callsite"]

            # source_inc =
            target_inc = self.df.loc[(self.df["name"] == target_name)][
                "time (inc)"
            ].max()

            inclusive_flow[(edge[0], edge[1])] = target_inc

        nx.set_edge_attributes(self.nxg, name="weight", values=inclusive_flow)
        # exc_capacity_mapping = self.calculate_exc_weight(self.g)
        # nx.set_edge_attributes(self.g, name="exc_weight", values=exc_capacity_mapping)

    def calculate_exc_weight(self, graph):
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
    def _calculate_flows(nxg):
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

    def dataset_map(self, nodes, dataset):
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
