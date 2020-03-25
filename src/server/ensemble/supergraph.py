import networkx as nx
from utils.logger import log
import math, json, utils
from ast import literal_eval as make_tuple
import numpy as np
from utils.timer import Timer

class SuperGraph(nx.Graph):
    # Attributes:
    # 1. State => Pass the state which needs to be handled.
    # 2. path => '', 'path', 'group_path' or 'component_path'
    # 3. construct_graph -> To decide if we should construct graph from path
    # 4. add_data => To
    def __init__(
        self, states, path, group_by_attr="module", construct_graph=True, add_data=False, reveal_callsites=[]
    ):
        super(SuperGraph, self).__init__()
        self.states = states
        self.timer = Timer()

        # Store the ensemble graph (Since it is already processed.)
        self.state_entire = self.states['ensemble_entire']
        self.state_filter = self.states['ensemble_filter']
        self.state_group = self.states['ensemble_group']
        self.ensemble_g = self.state_group.g
        self.node_list = np.array(list(self.ensemble_g.nodes()))

        # Path type to group by
        # TODO: Generalize to any group the user provides.
        self.path = path
        self.group_by = group_by_attr

        self.entire_df = self.state_entire.df
        self.group_df = self.state_group.df
        # Columns to consider.
        # TODO: Generalize it either all columns or let user specify the value using config.json
        self.columns = [
            "time (inc)",
            "module",
            # "group_path",
            "name",
            "time",
            # "callers",
            # "callees",
            # "vis_name",
            "module",
            # "show_node",
        ]

        # Store all the names of runs in self.runs.
        # TODO: Change name in the df from 'dataset' to 'run'
        self.runs = self.entire_df["dataset"].unique()

        self.reveal_callsites = reveal_callsites

        with self.timer.phase("Construct Graph"):
            if construct_graph:
                print("Creating a Graph for {0}.".format(self.state_group.name))
                self.mapper = {}
                self.g = nx.DiGraph()
                self.add_paths(path)
            else:
                print("Using the existing graph from state {0}".format(self.state.name))

        # Store the A (*adjacency matrix.)
        # with self.timer.phase("Create adjacency matrix"):
        #     self.adj_matrix = nx.adjacency_matrix(self.g)
        #     self.dense_adj_matrix = self.adj_matrix.todense()

        # Variables to control the data properties globally.
        self.callbacks = []
        self.edge_direction = {}

        add_data = True
        with self.timer.phase("Add graph attributes"):
            if add_data == True:
                self.add_node_attributes()
                self.add_edge_attributes()
            else:
                print("Creating a Graph without node or edge attributes.")
        print(self.timer)

    def rename_cycle_path(self, path):
        ret = []
        moduleMapper = {}
        dataMap = {}

        if(isinstance(path, float)):
            return []
        path = make_tuple(path)
        for idx, elem in enumerate(path):
            callsite = elem.split('=')[1]
            module = elem.split('=')[0]
            if (module not in dataMap):
                moduleMapper[module] = 0
                dataMap[module] =  [{
                    'callsite': callsite,
                    'module': module,
                    'level': idx
                }]
            else:
                flag = [p['level'] == idx for p in dataMap[module]]
                if np.any(np.array(flag)):
                    moduleMapper[module] += 1
                    dataMap[module].append({
                    'callsite': callsite,
                    'module': module,
                    'level': idx
                    })
                else:
                    dataMap[module].append({
                        'callsite': callsite,
                        'module': module,
                        'level': idx
                    })
            ret.append(dataMap[module][-1])

        return ret

    def add_reveal_paths(self):
        paths = []
        for callsite in self.reveal_callsites:
            df = self.entire_df.loc[self.entire_df['name'] == callsite]
            paths.append(df['group_path'].unique()[0])
        return np.array(paths)

    def add_paths(self, path):
        paths = self.group_df[path].unique()
        # print(paths, type(paths))
        # reveal_paths = self.add_reveal_paths()
        # print(reveal_paths, type(reveal_paths))

        # paths = np.concatenate((paths, reveal_paths), axis=0)

        for idx, path_str in enumerate(paths):
            path_list = self.rename_cycle_path(path_str)

            for callsite_idx, callsite in enumerate(path_list):
                if callsite_idx != len(path_list) - 1:
                    source = path_list[callsite_idx]
                    target = path_list[callsite_idx + 1]

                    if(not self.g.has_edge(source['module'], target['module'])):
                        source_module = source['module']
                        target_module = target['module']

                        source_name = source['callsite']
                        target_name = target['callsite']

                        if(self.g.has_edge(target['module'], source['module'])):
                            edge_type = 'callback'
                        else:
                            edge_type = 'normal'

                        if(edge_type == 'normal'):
                            self.g.add_edge(source_module, target_module,   attr_dict={
                                "source_callsite": source_name,
                                "target_callsite": target_name,
                                "edge_type": edge_type
                            })

        # reveal_paths = self.add_reveal_paths()
        # for reveal_path_str in reveal_paths:
        #     reveal_path_list = self.rename_cycle_path(reveal_path_str)
        #     print(reveal_path_list)
        #     callsite_idx = len(reveal_path_list) - 2
        #     source = reveal_path_list[callsite_idx]
        #     target = reveal_path_list[callsite_idx + 1]

        #     if(not self.g.has_edge(target['module'], target['module'] + '=' + target_name)):
        #         source_module = source['module']
        #         target_module = target['module']

        #         source_name = self.reveal_callsites[0]
        #         target_name = target['callsite']

        #         print(f"Adding edge: {source_name}, {target_name}")
        #         self.g.add_edge(target_module, target_module + '=' + target_name, attr_dict={
        #             "source_callsite": source_name,
        #             "target_callsite": target_name
        #         })
            
    def add_node_attributes(self):
        ensemble_mapping = self.ensemble_map(self.g.nodes())

        for idx, key in enumerate(ensemble_mapping):
            nx.set_node_attributes(self.g, name=key, values=ensemble_mapping[key])

        dataset_mapping = {}
        for run in self.runs:
            dataset_mapping[run] = self.dataset_map(self.g.nodes(), run)

            nx.set_node_attributes(
                self.g, name=run, values=dataset_mapping[run]
            )

    def add_edge_attributes(self):
        # number_of_runs_mapping = self.number_of_runs()
        # nx.set_edge_attributes(self.g, name="number_of_runs", values=number_of_runs_mapping)
        capacity_mapping = self.calculate_flows(self.g)
        nx.set_edge_attributes(self.g, name="weight", values=capacity_mapping)
        exc_capacity_mapping = self.calculate_exc_weight(self.g)
        nx.set_edge_attributes(self.g, name="exc_weight", values=exc_capacity_mapping)

    def number_of_runs(self):
        ret = {}
        for idx, run in enumerate(self.runs):
            for edge in self.states[run].g.edges():
                source = edge[0]
                target = edge[1]
                source_module = self.df.loc[self.df['name'] == source]['module'].unique()[0]
                target_module = self.df.loc[self.df['name'] == target]['module'].unique()[0]

                edge_with_module = (source_module + '=' + source, target_module + '=' + target)
                if edge_with_module not in ret:
                    ret[edge_with_module] = 0
                ret[edge_with_module] += 1
        return ret

    def tailhead(self, edge):
        return (edge[0], edge[1])

    def tailheadDir(self, edge):
        return (str(edge[0]), str(edge[1]), self.edge_direction[edge])

    def leaves_below(self, graph, node):
        return set(
            sum(
                (
                    [vv for vv in v if graph.out_degree(vv) == 0]
                    for k, v in nx.dfs_successors(graph, node).items()
                ),
                [],
            )
        )

    def calculate_flows(self, graph):
        ret = {}
        additional_flow = {}
        for edge in graph.edges(data=True):
            if('=' in edge[0]):
                source_module = edge[0].split('=')[0]
            else:
                source_module = edge[0]

            if('=' in edge[1]):
                target_module = edge[1].split('=')[0]
            else:
                target_module = edge[1]

            source_inc = self.entire_df.loc[(self.entire_df["module"] == source_module)][
                "time (inc)"
            ].max()
            target_inc = self.entire_df.loc[(self.entire_df["module"] == target_module)][
                "time (inc)"
            ].max()

            ret[(edge[0], edge[1])] = target_inc

        return ret

    def calculate_exc_weight(self, graph):
        ret = {}
        additional_flow = {}
        for edge in graph.edges(data=True):
            source_name = edge[2]['attr_dict']['source_callsite']
            target_name = edge[2]['attr_dict']['target_callsite']

            source_exc = self.entire_df.loc[(self.entire_df["name"] == source_name)]["time"].max()
            target_exc = self.entire_df.loc[(self.entire_df["name"] == target_name)]["time"].max()

            ret[(edge[0], edge[1])] = target_exc

        return ret

    def ensemble_map(self, nodes):
        ret = {}

        ensemble_columns = []
        for column in self.columns:
            ensemble_columns.append(column)

        new_columns = ["max_inc_time", "max_exc_time", "dist_inc_time", "dist_exc_time"]
        ensemble_columns.append("dist_inc_time")
        ensemble_columns.append("dist_exc_time")

        # loop through the nodes
        for node in self.g.nodes():
            if "=" in node:
                node_name = node.split("=")[0]
            else:
                node_name = node

            # Get their dataframe
            node_df = self.entire_df.loc[self.entire_df["module"] == node_name]

            for column in ensemble_columns:
                if column not in ret:
                    ret[column] = {}

                if(column not in new_columns):
                    column_data = node_df[column]

                if (
                    column == "time (inc)"
                    or column == "time"
                    or column == "component_level"
                ):
                    if len(column_data.value_counts() > 0):
                        ret[column][node] = column_data.max()
                    else:
                        ret[column][node] = -1

                elif column == "callers" or column == "callees":

                    if len(column_data.value_counts()) > 0:
                        ret[column][node] = column_data.tolist()
                    else:
                        ret[column][node] = []

                elif (
                    column == "name"
                    or column == "module"
                    or column == "show_node"
                ):

                    if len(column_data.value_counts() > 0):
                        ret[column][node] = column_data.tolist()[0]
                    else:
                        ret[column][node] = "None"

                elif column == "component_path" or column == "group_path":
                    if len(column_data.value_counts() > 0):
                        ret[column][node] = list(make_tuple(column_data.tolist()[0]))
                    else:
                        ret[column][node] = []

                elif column == 'dist_inc_time':
                    if len(node_df['time (inc)'].value_counts() > 0):
                        ret[column][node] = node_df['time (inc)'].tolist()
                    else:
                        ret[column][node] = []

                elif column == 'dist_exc_time':
                    if len(node_df['time'].value_counts() > 0):
                        ret[column][node] = node_df['time'].tolist()
                    else:
                        ret[column][node] = []
        return ret

    def dataset_map(self, nodes, dataset):
        ret = {}
        for node in self.g.nodes():
            if "=" in node:
                node_name = node.split("=")[0]
            else:
                node_name = node

            if node not in ret:
                ret[node] = {}

            node_df = self.entire_df.loc[
                (self.entire_df["module"] == node_name) & (self.entire_df["dataset"] == dataset)
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
                        ret[node][column] = column_data.tolist()
                    else:
                        ret[node][column] = []

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

                elif column == "component_path" or column == "group_path":

                    if len(column_data.value_counts() > 0):
                        ret[node][column] = list(make_tuple(column_data.tolist()[0]))
                    else:
                        ret[node][column] = []
        return ret