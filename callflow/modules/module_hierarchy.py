# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT


# ------------------------------------------------------------------------------
# Library imports
import networkx as nx

# ------------------------------------------------------------------------------
# CallFlow imports
import callflow
LOGGER = callflow.get_logger(__name__)

class ModuleHierarchy:
    def __init__(self, supergraph, module, filter_by="time (inc)", filter_perc=10.0):
        self.df = supergraph.gf.df
        self.module = module

        self.hierarchy = ModuleHierarchy.create_nxg_tree_from_paths(df=supergraph.gf.df, path="path", filter_by=filter_by, filter_perc=filter_perc )

        cycles = self.check_cycles(self.hierarchy)
        while len(cycles) != 0:
            self.hierarchy = self.remove_cycles(self.hierarchy, cycles)
            cycles = self.check_cycles(self.hierarchy)
            print(f"cycles: {cycles}")

    @staticmethod
    def create_nxg_tree_from_paths(self, df, path_name, filter_by, filter_perc):
        """
        Create a networkx graph for the module hierarchy.
        Filter if filter percentage is greater than 0.
        """
        if filter_perc > 0.0:
            group_df = module_df.groupby(["name"]).mean()
            f_group_df = group_df.loc[group_df[filter_by] > filter_perc * group_df[filter_by].max()]
            callsites = f_group_df.index.values.tolist()
            df = df[df["name"].isin(callsites)]

        paths = df[path_name].unique()
        for idx, path in enumerate(paths):
            if isinstance(path, float):
                return []
            path = make_tuple(path)
            source_targets = ModuleHierarchy._create_source_targets(path)
            for edge in source_targets:
                source = edge["source"]
                target = edge["target"]
                if not self.hierarchy.has_edge(source, target):
                    self.hierarchy.add_edge(source, target)

    @staticmethod
    def _create_source_targets(path):
        """
        Create edges from path.

        Params:
            path (list) - paths expressed as a list.

        Return:
            edges (array) - edges expressed as source-target pairs.
        """
        edges = []

        for idx, callsite in enumerate(path):
            if idx == len(path) - 1:
                break

            source = sanitizeName(path[idx])
            target = sanitizeName(path[idx + 1])

            edges.append({"source": source, "target": target})
        return edges

    @staticmethod
    def as_spanning_trees(G):
        """
        For a given graph with multiple sub graphs, find the components
        and draw a spanning tree.

        Returns a new Graph with components as spanning trees (i.e. without cycles).
        """
        ret = nx.Graph()
        graphs = nx.connected_component_subgraphs(G, copy=False)

        for g in graphs:
            T = nx.minimum_spanning_tree(g)
            ret.add_edges_from(T.edges())
            ret.add_nodes_from(T.nodes())

        return ret

    @staticmethod
    def check_cycles(G):
        """
        Checks if there are cycles.

        Return:
            The cycles in the graph.
        """
        try:
            cycles = list(nx.find_cycle(self.hierarchy, orientation="ignore"))
        except:
            cycles = []

        return cycles

    @staticmethod
    def _remove_cycles(G, cycles):
        """
        Removes cycles from the networkX Graph.
        TODO: Improve the logic here.
        """
        for cycle in cycles:
            source = cycle[0]
            target = cycle[1]
            print("Removing edge:", source, target)
            if source == target:
                print("here")
                G.remove_edge(source, target)
                G.remove_node(source)
                G.remove_node

            if cycle[2] == "reverse":
                print("Removing edge:", source, target)
                G.remove_edge(source, target)
        return G
