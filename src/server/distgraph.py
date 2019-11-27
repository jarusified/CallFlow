import networkx as nx
from logger import log
import math, json, utils
from ast import literal_eval as make_tuple


class DistGraph(nx.Graph):
    # Attributes:
    # 1. State => Pass the state which needs to be handled.
    # 2. path => '', 'path', 'group_path' or 'component_path'
    # 3. construct_graph -> To decide if we should construct graph from path
    # 4. add_data => To
    def __init__(
        self, state, path, group_by_attr="module", construct_graph=True, add_data=True
    ):
        super(DistGraph, self).__init__()
        self.state = state
        self.path = path
        self.df = self.state.df
        self.group_by = group_by_attr
        #         self.columns = ['time']
        self.columns = [
            "time (inc)",
            "group_path",
            "name",
            "time",
            "callers",
            "callees",
            "vis_name",
            "module",
            "show_node",
        ]

        if construct_graph:
            print("Creating a Graph for {0}.".format(self.state.name))
            self.g = nx.DiGraph()
            self.add_paths(path)
        else:
            print("Using the existing graph from state {0}".format(state.name))
            self.g = state.g

        self.adj_matrix = nx.adjacency_matrix(self.g)
        self.dense_adj_matrix = self.adj_matrix.todense()

        self.callbacks = []
        self.edge_direction = {}

        if add_data == True:
            self.add_node_attributes()
            self.add_edge_attributes()
        else:
            print("Creating a Graph without node or edge attributes.")
        self.adj_matrix = nx.adjacency_matrix(self.g)
        self.dense_adj_matrix = self.adj_matrix.todense()

    def no_cycle_path(self, path):
        ret = []
        mapper = {}
        for idx, elem in enumerate(path):
            if elem not in mapper:
                mapper[elem] = 1
                ret.append(elem)
            else:
                ret.append(elem + "_" + str(mapper[elem]))
                mapper[elem] += 1

        return tuple(ret)

    def add_paths(self, path):
        for idx, row in self.df.iterrows():
            if row.show_node:
                if isinstance(row[path], list):
                    path_tuple = row[path]
                elif isinstance(row[path], str):
                    path_tuple = make_tuple(row[path])
                corrected_path = self.no_cycle_path(path_tuple)
                self.g.add_path(corrected_path)

    def add_node_attributes(self):
        ensemble_mapping = self.ensemble_map(self.g.nodes())

        for idx, key in enumerate(ensemble_mapping):
            nx.set_node_attributes(self.g, name=key, values=ensemble_mapping[key])

        dataset_mapping = {}
        for dataset in self.df["dataset"].unique():
            dataset_mapping[dataset] = self.dataset_map(self.g.nodes(), dataset)

            nx.set_node_attributes(
                self.g, name=dataset, values=dataset_mapping[dataset]
            )

    def add_edge_attributes(self):
        # number_of_runs_mapping = self.number_of_runs()
        # nx.set_edge_attributes(
        #     self.g, name="number_of_runs", values=number_of_runs_mapping
        # )
        capacity_mapping = self.calculate_flows(self.g)
        nx.set_edge_attributes(self.g, name="weight", values=capacity_mapping)
        exc_capacity_mapping = self.calculate_exc_weight(self.g)
        nx.set_edge_attributes(self.g, name="exc_weight", values=exc_capacity_mapping)

    def number_of_runs(self):
        ret = {}
        for idx, name in enumerate(self.runs):
            for edge in self.runs[name].edges():
                if edge not in ret:
                    ret[edge] = 0
                ret[edge] += 1
        return ret

    def add_union_node_attributes(self):
        for node in self.R.nodes(data=True):
            node_name = node[0]
            node_data = node[1]
            max_inc_time = 0
            max_exc_time = 0
            self.R.nodes[node_name]["ensemble"] = {}
            for dataset in node_data:
                for idx, key in enumerate(node_data[dataset]):
                    if key == "name":
                        self.R.nodes[node_name]["union"]["name"] = node_data[dataset][
                            key
                        ]
                    elif key == "time (inc)":
                        max_inc_time = max(max_inc_time, node_data[dataset][key])
                    elif key == "time":
                        max_exc_time = max(max_exc_time, node_data[dataset][key])
                    elif key == "entry_functions":
                        entry_functions = node_data[dataset][key]

            self.R.nodes[node_name]["ensemble"]["time (inc)"] = max_inc_time
            self.R.nodes[node_name]["ensemble"]["time"] = max_exc_time
            self.R.nodes[node_name]["ensemble"]["entry_functions"] = entry_functions

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
        edges = graph.edges()
        additional_flow = {}
        for edge in edges:
            if "=" in edge[0]:
                source_name = edge[0].split("=")[1]
                source_module = edge[0].split("=")[0]
            else:
                source_name = edge[1]
                source_module = self.df.loc[self.df["name"] == source_name]["module"][0]

            if "=" in edge[1]:
                target_name = edge[1].split("=")[1]
                target_module = edge[1].split("=")[0]
            else:
                target_name = edge[1]
                target_module = self.df.loc[self.df["name"] == target_name]["module"][0]

            source_inc = self.df.loc[(self.df["name"] == source_name)][
                "time (inc)"
            ].max()
            target_inc = self.df.loc[(self.df["name"] == target_name)][
                "time (inc)"
            ].max()

            if source_inc == target_inc:
                ret[edge] = source_inc
            else:
                ret[edge] = target_inc

        return ret

    def calculate_exc_weight(self, graph):
        ret = {}
        edges = graph.edges()
        additional_flow = {}
        for edge in edges:
            if "=" in edge[0]:
                source_name = edge[0].split("=")[1]
                source_module = edge[0].split("=")[0]
            else:
                source_name = edge[1]
                source_module = self.df.loc[self.df["name"] == source_name]["module"][0]

            if "=" in edge[1]:
                target_name = edge[1].split("=")[1]
                target_module = edge[1].split("=")[0]
            else:
                target_name = edge[1]
                target_module = self.df.loc[self.df["name"] == target_name]["module"][0]

            source_inc = self.df.loc[(self.df["name"] == source_name)]["time"].max()
            target_inc = self.df.loc[(self.df["name"] == target_name)]["time"].max()

            if source_inc == target_inc:
                ret[edge] = source_inc
            else:
                ret[edge] = target_inc

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
                node_name = node.split("=")[1]
            else:
                node_name = node

            # Get their dataframe
            node_df = self.df.loc[self.df["name"] == node_name]

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
                        ret[column][node] = make_tuple(column_data.tolist()[0])
                    else:
                        ret[column][node] = []

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
                node_name = node.split("=")[1]
            else:
                node_name = node

            if node not in ret:
                ret[node] = {}

            node_df = self.df.loc[
                (self.df["name"] == node_name) & (self.df["dataset"] == dataset)
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