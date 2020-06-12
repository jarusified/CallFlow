# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# ------------------------------------------------------------------------------
# Library imports
import math
import pandas as pd
import networkx as nx
import ast
#from ast import literal_eval as make_tuple

# ------------------------------------------------------------------------------
# CallFlow imports
import callflow
from callflow.timer import Timer
from callflow import SuperGraph


# ------------------------------------------------------------------------------
# CCT Rendering class.
class Render_CCT(SuperGraph):

    def __init__(self, supergraphs, tag, props, callsite_count=50):

        super().__init__(props=props, tag=tag, mode="render")

        print ('len of supergraphs = ', len(supergraphs))
        print ('keys of supergraphs = ', supergraphs.keys())
        print ('supergraphs[calc-pi] = ', supergraphs['calc-pi'])
        print ('tag = ', tag)
        print ('callsite_count = ', callsite_count)
        print ('props = ', props)
        assert isinstance(callsite_count, int)
        assert callsite_count > 0


        # set the current graph being rendered.
        self.supergraph = supergraphs[tag]

        # Number of runs in the state.
        self.runs = self.supergraph.gf.df['dataset'].unique()
        self.columns = ["time (inc)", "time", "name", "module"]

        # callsite count is bounded by the user's input.
        '''
        if callsite_count == None:
            self.callsite_count = len(self.supergraph.gf.df["name"].unique())
        else:
            self.callsite_count = int(callsite_count)
        '''

        # Put the top callsites into a list.
        callsites = self.supergraph.gf.get_top_by_attr(callsite_count, "time (inc)")

        print ('found callsites: ', callsites)
        print ('found callsites: ', len(callsites))
        '''
        self.callsites = self.get_top_n_callsites_by_attr(
            df=self.supergraph.gf.df,
            callsite_count=self.callsite_count,
            sort_attr="time (inc)",
        )
        '''

        # Filter out the callsites not in the list.
        print('filtering by name')
        self.supergraph.gf.filter_by_name(callsites)

        '''
        self.supergraph.gf.df = self.supergraph.gf.df[
            self.supergraph.gf.df["name"].isin(self.callsites)
        ]
        '''
        #print('getting unique')
        #self.datasets = self.supergraph.gf.df['dataset'].unique()
        #print('unique =', self.datasets)
        #print ('nxg = ', self.supergraph.gf.nxg)


        with self.timer.phase(f"Creating the ensemble CCT: {self.runs}"):

            self.supergraph.gf.nxg = nx.DiGraph()
            print ('before adding paths')
            print (self.supergraph.gf.nxg.number_of_nodes(),
                   self.supergraph.gf.nxg.number_of_edges())

            # Add paths by "column" = path.
            #self.add_paths("path")
            self.add_paths()

            print ('after adding paths')
            print (self.supergraph.gf.nxg.number_of_nodes(), self.supergraph.gf.nxg.number_of_edges())



        # Add node and edge attributes.
        with self.timer.phase(f"Add node and edge attributes."):
            self.add_node_attributes()
            self.add_edge_attributes()

        # Find cycles in the Render_CCT.
        with self.timer.phase(f"Find cycles"):
            self.supergraph.gf.nxg.cycles = Render_CCT.find_cycle(self.supergraph.gf.nxg)

        print(self.timer)

    # --------------------------------------------------------------------------
    def _remove_get_top_n_callsites_by_attr(
        self, df=pd.DataFrame([]), callsite_count=50, sort_attr="time (inc)"
    ):
        """
        Fetches the top n callsites based on attribute (time/time (inc)).
        """
        xgroup_df = self.supergraph.gf.df.groupby(["name"]).mean()
        sort_xgroup_df = xgroup_df.sort_values(by=[sort_attr], ascending=False)
        callsites_df = sort_xgroup_df.nlargest(callsite_count, sort_attr)
        return callsites_df.index.values.tolist()

    def _remove_ensemble_map(self, df, nodes):
        ret = {}
        """
        Construct the ensemble map
        """
        for callsite in self.supergraph.gf.nxg.nodes():
            if callsite not in self.props["callsite_module_map"]:
                module = self.supergraph.gf.df.loc[
                    self.supergraph.gf.df["name"] == callsite
                ]["module"].unique()[0]
            else:
                module = self.props["callsite_module_map"][callsite]

            for column in self.columns:
                if column not in ret:
                    ret[column] = {}
                if column == "time (inc)":
                    ret[column][callsite] = self.name_time_inc_map[(module, callsite)]
                elif column == "time":
                    ret[column][callsite] = self.name_time_exc_map[(module, callsite)]
                elif column == "name":
                    ret[column][callsite] = callsite
                elif column == "module":
                    ret[column][callsite] = module

        return ret

    def _remove_dataset_map(self, nodes, run):
        """
        Construct maps for each dataset.
        """
        ret = {}
        for callsite in self.supergraph.gf.nxg.nodes():
            if callsite not in self.props["callsite_module_map"]:
                module = self.supergraph.gf.df.loc[
                    self.supergraph.gf.df["name"] == callsite
                ]["module"].unique()[0]
            else:
                module = self.props["callsite_module_map"][callsite]

            if callsite in self.target_module_callsite_map[run].keys():
                if callsite not in ret:
                    ret[callsite] = {}

                for column in self.columns:
                    if column == "time (inc)":
                        ret[callsite][column] = self.target_module_time_inc_map[run][
                            module
                        ]

                    elif column == "time":
                        ret[callsite][column] = self.target_module_time_exc_map[run][
                            module
                        ]

                    elif column == "module":
                        ret[callsite][column] = module

                    elif column == "name":
                        ret[callsite][column] = callsite

        return ret

    def _remove_edge_map(self, edges, attr, source=None, orientation=None):
        counter = {}
        if not self.supergraph.gf.nxg.is_directed() or orientation in (
            None,
            "original",
        ):

            def tailhead(edge):
                return edge[:2]

        elif orientation == "reverse":

            def tailhead(edge):
                return edge[1], edge[0]

        elif orientation == "ignore":

            def tailhead(edge):
                if edge[-1] == "reverse":
                    return edge[1], edge[0]
                return edge[:2]

        ret = {}
        explored = []
        for start_node in self.supergraph.gf.nxg.nbunch_iter(source):
            if start_node in explored:
                # No loop is possible.
                continue

            edges = []
            # All nodes seen in this iteration of edge_dfs
            seen = {start_node}
            # Nodes in active path.
            active_nodes = {start_node}
            previous_head = None

            for edge in nx.edge_dfs(self.supergraph.gf.nxg, start_node, orientation):

                tail, head = tailhead(edge)
                if edge not in counter:     counter[edge] = 0
                if tail == head:            counter[edge] += 1
                else:                       counter[edge] = 1

        return counter

    def _remove_create_source_targets(self, path):
        module = ""
        edges = []

        for idx, callsite in enumerate(path):
            if idx == len(path) - 1:
                break

            source = callflow.utils.sanitize_name(path[idx])
            target = callflow.utils.sanitize_name(path[idx + 1])

            edges.append(
                {"source": source, "target": target,}
            )
        return edges

    # --------------------------------------------------------------------------

    @staticmethod
    def _tailhead(edge, is_directed, orientation=None):

        # Probably belongs on graphframe?
        # definitaly also used in supergraph
        assert isinstance(edge, tuple)
        assert len(edge) == 2
        assert isinstance(is_directed, bool)
        #assert isinstance(orientation, (NoneType,str))

        if not is_directed or orientation in [None, 'original']: return edge[0], edge[1]
        elif orientation == "reverse":                           return edge[1], edge[0]
        elif orientation == "ignore" and edge[-1] == "reverse":  return edge[1], edge[0]
        return edge[0], edge[1]

    # --------------------------------------------------------------------------
    def add_node_attributes(self):

        '''
        datamap = self.ensemble_map(
            self.supergraph.gf.df, self.supergraph.gf.nxg.nodes()
        )
        '''
        # ----------------------------------------------------------------------
        # TODO: probably belongs to supergraph
        def _get_module_name(callsite):
            if callsite in self.props['callsite_module_map']:
                return self.props['callsite_module_map'][callsite]
            #else:
            return self.supergraph.gf.lookup_with_name(callsite)['module'].unique()[0]

        # ----------------------------------------------------------------------
        # compute data map
        datamap = {}
        for callsite in self.supergraph.gf.nxg.nodes():

            module = _get_module_name(callsite)

            for column in self.columns:
                if column not in datamap:
                   datamap[column] = {}

                if column == "time (inc)":
                    datamap[column][callsite] = self.name_time_inc_map[(module, callsite)]
                elif column == "time":
                    datamap[column][callsite] = self.name_time_exc_map[(module, callsite)]
                elif column == "name":
                    datamap[column][callsite] = callsite
                elif column == "module":
                    datamap[column][callsite] = module

        # ----------------------------------------------------------------------
        for idx, key in enumerate(datamap):
            nx.set_node_attributes(self.supergraph.gf.nxg,
                                        name=key, values=datamap[key])

        # ----------------------------------------------------------------------
        # compute map across data
        for run in self.runs:

            datamap = {}
            for callsite in self.supergraph.gf.nxg.nodes():

                if callsite not in self.target_module_callsite_map[run].keys():
                    continue

                module = _get_module_name(callsite)

                if callsite not in datamap:
                    datamap[callsite] = {}

                for column in self.columns:

                    if column not in datamap:
                       datamap[column] = {}

                    if column == "time (inc)":
                        datamap[callsite][column] = self.target_module_time_inc_map[run][module]
                    elif column == "time":
                        datamap[callsite][column] = self.target_module_time_exc_map[run][module]
                    elif column == "module":
                        datamap[callsite][column] = module
                    elif column == "name":
                        datamap[callsite][column] = callsite

            # ------------------------------------------------------------------
            nx.set_node_attributes(self.supergraph.gf.nxg,
                                        name=run, values=datamap)

    # --------------------------------------------------------------------------
    def add_edge_attributes(self):
        '''
        num_of_calls_mapping = self.edge_map(
            self.supergraph.gf.nxg.edges(), "component_path"
        )
        '''
        #attr = 'component_path'

        # ----------------------------------------------------------------------
        source = None
        orientation = None
        is_directed = self.supergraph.gf.nxg.is_directed()

        edge_counter = {}

        #ret = {}
        #explored = []
        for start_node in self.supergraph.gf.nxg.nbunch_iter(source):

            # never adding to explored!
            #if start_node in explored:      # No loop is possible.
            #    continue

            #edges = []
            # All nodes seen in this iteration of edge_dfs
            #seen = {start_node}
            # Nodes in active path.
            #active_nodes = {start_node}
            #previous_head = None

            for edge in nx.edge_dfs(self.supergraph.gf.nxg, start_node, orientation):

                tail, head = Render_CCT._tailhead(edge, is_directed, orientation)

                if edge not in edge_counter:    edge_counter[edge] = 0

                if tail == head:                edge_counter[edge] += 1
                else:                           edge_counter[edge] = 1

        # ----------------------------------------------------------------------
        nx.set_edge_attributes(self.supergraph.gf.nxg,
                                name='count', values=edge_counter)

    # --------------------------------------------------------------------------
    def add_paths(self):

        paths = self.supergraph.gf.df['path'].tolist()

        from ast import literal_eval as make_tuple

        # go over all path
        for i, path in enumerate(paths):

            # go over the callsites in this path
            callsites = make_tuple(path)
            plen = len(callsites)

            #print ('\n -- path {} has {} callsites'.format(i, plen))

            for j in range(plen-1):
                source = callflow.utils.sanitize_name(callsites[j])
                target = callflow.utils.sanitize_name(callsites[j+1])

                #print ('testing {} -- {}'.format(source, target))
                if not self.supergraph.gf.nxg.has_edge(source, target):
                    self.supergraph.gf.nxg.add_edge(source, target)
                    #print (' >> adding {} -- {}'.format(source, target))

            '''
            # why is this needed?
            if isinstance(path, float):
                assert False
                return []

            source_targets = self.create_source_targets(path)

            # add all the edges
            for edge in source_targets:
                source = edge["source"]
                target = edge["target"]
                if not self.supergraph.gf.nxg.has_edge(source, target):
                    self.supergraph.gf.nxg.add_edge(source, target)
            '''

    # --------------------------------------------------------------------------
    @staticmethod
    def find_cycle(G, source=None, orientation=None):
        '''
        if not G.is_directed() or orientation in (None, "original"):

            def tailhead(edge):
                return edge[:2]

        elif orientation == "reverse":

            def tailhead(edge):
                return edge[1], edge[0]

        elif orientation == "ignore":

            def tailhead(edge):
                if edge[-1] == "reverse":
                    return edge[1], edge[0]
                return edge[:2]
        '''
        explored = set()
        cycle = []
        count = 0
        final_node = None
        is_directed = G.is_directed()
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
                tail, head = Render_CCT._tailhead(edge, is_directed, orientation)
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
                            popped_head = Render_CCT._tailhead(popped_edge, is_directed, orientation)[1]
                            active_nodes.remove(popped_head)

                        if edges:
                            # how can you pass a single element into tailhead?
                            assert False
                            last_head = Render_CCT._tailhead(edges[-1], is_directed, orientation)[1]
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
            assert len(cycle) == 0
            # raise nx.exception.NetworkXNoCycle('No cycle found.')

        # We now have a list of edges which ends on a cycle.
        # So we need to remove from the beginning edges that are not relevant.
        i = 0
        for i, edge in enumerate(cycle):
            tail, head = Render_CCT._tailhead(edge, is_directed, orientation)
            if tail == final_node:
                break
        return cycle[i:]

    # --------------------------------------------------------------------------
