##############################################################################
# Copyright (c) 2018-2019, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Callflow.
# Created by Suraj Kesavan <kesavan1@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# For details, see: https://github.com/LLNL/Callflow
# Please also read the LICENSE file for the MIT License notice.
##############################################################################

import pandas as pd
import networkx as nx
from ast import literal_eval as make_tuple
import math
import utils

class CCT:
    def __init__(self, state, functionsInCCT):
        number_of_nodes = len(state.df['name'].unique())

        # Get the top most callsites from the CCT.
        if(number_of_nodes < int(functionsInCCT)):
            self.entire_graph = state.g
            self.entire_df = state.df
        else:
            self.entire_graph = state.g
            self.entire_df = state.df
        self.run()

    # def add_node_attributes(self):
    #     time_inc_mapping = self.node_map(self.g.nodes(), 'time (inc)')
    #     nx.set_node_attributes(self.g, name='time (inc)', values=time_inc_mapping)

    #     time_mapping = self.node_map(self.g.nodes(), 'time')
    #     nx.set_node_attributes(self.g, name='time', values=time_mapping)

        # module_mapping = self.node_map(self.g.nodes(), 'module')
        # nx.set_node_attributes(self.g, name='module', values=module_mapping)


        # imbalance_perc_mapping = self.node_map(self.g.nodes(), 'imbalance_perc')
        # nx.set_node_attributes(self.g, name='imbalance_perc', values=imbalance_perc_mapping)

    def ensemble_map(self, nodes):
        ret = {}

        ensemble_columns = []
        for column in self.entire_df.columns:
            ensemble_columns.append(column)

        # loop through the nodes
        for node in self.g.nodes():
            print(node)

            # Get their dataframe
            node_df = self.entire_df.loc[self.entire_df["name"] == node]
            column_data = node_df[column]

            for column in ensemble_columns:
                if column not in ret:
                    ret[column] = {}

                if (
                    column == "time (inc)"
                    or column == "time"
                    or column == "component_level"
                ):
                    if len(column_data.value_counts() > 0):
                        ret[column][node] = column_data.max()
                    else:
                        ret[column][node] = -1

                # elif column == "callers" or column == "callees":

                #     if len(column_data.value_counts()) > 0:
                #         ret[column][node] = make_tuple(column_data.tolist()[0])
                #     else:
                #         ret[column][node] = []

                elif (
                    column == "name"
                    or column == "vis_name"
                    or column == "module"
                    or column == "show_node"
                ):

                    if len(column_data.value_counts() > 0):
                        ret[column][node] = column_data.tolist()[0]
                    else:
                        ret[column][node] = "None"


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

            node_df = self.entire_df.loc[
                (self.entire_df["name"] == node_name) & (self.entire_df["dataset"] == dataset)
            ]

            for column in self.entire_df.columns:
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

                elif (
                    column == "name"
                    or column == "vis_name"
                    or column == "module"
                    or column == "show_node"
                ):
                    if len(column_data.value_counts()) > 0:
                        ret[node][column] = column_data.tolist()[0]

                    else:
                        ret[node][column] = "None"

        return ret

    def add_node_attributes(self):
        ensemble_mapping = self.ensemble_map(self.g.nodes())

        for idx, key in enumerate(ensemble_mapping):
            nx.set_node_attributes(self.g, name=key, values=ensemble_mapping[key])

        # dataset_mapping = {}
        # for run in self.runs:
        #     dataset_mapping[run] = self.dataset_map(self.g.nodes(), run)

        #     nx.set_node_attributes(
        #         self.g, name=run, values=dataset_mapping[run]
        #     )

    def add_edge_attributes(self):
        num_of_calls_mapping = self.edge_map(self.g.edges(), 'component_path')
        nx.set_edge_attributes(self.g, name='count', values=num_of_calls_mapping)

    def node_map(self, nodes, attr):
        ret = {}
        # print(self.entire_df['name'])
        for node in nodes:
            data = self.entire_df.loc[self.entire_df['name'] == node]
            print(node, data[attr].unique())
            if attr == 'time' or attr == 'time (inc)' or attr == 'imbalance_perc':
                if( not math.isnan(data[attr].mean())):
                    ret[node] = data[attr].mean()
            else:
                ret[node] = data[attr].unique()
                print(ret[node])
        return ret

    def edge_map(self, edges, attr, source=None, orientation=None):
        counter = {}
        if not self.g.is_directed() or orientation in (None, 'original'):
            def tailhead(edge):
                return edge[:2]
        elif orientation == 'reverse':
            def tailhead(edge):
                return edge[1], edge[0]
        elif orientation == 'ignore':
            def tailhead(edge):
                if edge[-1] == 'reverse':
                    return edge[1], edge[0]
                return edge[:2]
        ret = {}
        explored = []
        for start_node in self.g.nbunch_iter(source):
            if start_node in explored:
                # No loop is possible.
                continue

            edges = []
            # All nodes seen in this iteration of edge_dfs
            seen = {start_node}
            # Nodes in active path.
            active_nodes = {start_node}
            previous_head = None

            for edge in nx.edge_dfs(self.g, start_node, orientation):
                tail, head = tailhead(edge)
                if(edge not in counter):
                    counter[edge] = 0
                if(tail == head):
                    counter[edge] += 1
                else:
                    counter[edge] = 1

        return counter

    def add_paths(self, path):
        path_df = self.entire_df[path].fillna("()")
        paths = path_df.drop_duplicates().tolist()

        for idx, path in enumerate(paths):
            path = path.split(',')
            if(len(path) >= 2):
                source = path[-2].replace('[', '').replace(']', '').replace("'", '')
                target = path[-1].replace('[', '').replace(']', '').replace("'", '')
                edge = (source, target)

                self.g.add_edge(source, target)

    def find_cycle(self, G, source=None, orientation=None):
        if not G.is_directed() or orientation in (None, 'original'):
            def tailhead(edge):
                return edge[:2]
        elif orientation == 'reverse':
            def tailhead(edge):
                return edge[1], edge[0]
        elif orientation == 'ignore':
            def tailhead(edge):
                if edge[-1] == 'reverse':
                    return edge[1], edge[0]
                return edge[:2]

        explored = set()
        cycle = []
        count = 0
        final_node = None
        for start_node in G.nbunch_iter(source):
            if start_node in explored:
                # No loop is possible.
                continue

            edges = []
            # All nodes seen in this iteration of edge_dfs
            seen = {start_node}
            # Nodes in active path.
            active_nodes = {start_node}
            previous_head = None

            for edge in nx.edge_dfs(G, start_node, orientation):
                # Determine if this edge is a continuation of the active path.
                tail, head = tailhead(edge)
                if head in explored:
                    # Then we've already explored it. No loop is possible.
                    continue
                if previous_head is not None and tail != previous_head:
                    # This edge results from backtracking.
                    # Pop until we get a node whose head equals the current tail.
                    # So for example, we might have:
                    #  (0, 1), (1, 2), (2, 3), (1, 4)
                    # which must become:
                    #  (0, 1), (1, 4)
                    while True:
                        try:
                            popped_edge = edges.pop()
                        except IndexError:
                            edges = []
                            active_nodes = {tail}
                            break
                        else:
                            popped_head = tailhead(popped_edge)[1]
                            active_nodes.remove(popped_head)

                        if edges:
                            last_head = tailhead(edges[-1])[1]
                            if tail == last_head:
                                break
                edges.append(edge)

                if head in active_nodes:
                    # We have a loop!
                    cycle.extend(edges)
                    final_node = head
                    break
                else:
                    seen.add(head)
                    active_nodes.add(head)
                    previous_head = head

            if cycle:
                count += 1
                break
            else:
                explored.update(seen)

        else:
            assert(len(cycle) == 0)
            # raise nx.exception.NetworkXNoCycle('No cycle found.')

        # We now have a list of edges which ends on a cycle.
        # So we need to remove from the beginning edges that are not relevant.
        i = 0
        for i, edge in enumerate(cycle):
            tail, head = tailhead(edge)
            if tail == final_node:
                break
        return cycle[i:]

    def run(self):
        self.g = nx.DiGraph()
        self.add_paths('path')
        self.add_node_attributes()
        self.add_edge_attributes()
        self.g.cycles = self.find_cycle(self.g)
