import os
import networkx as nx
import pandas as pd
import callflow
from callflow import GraphFrame, SuperGraph

LOGGER = callflow.get_logger(__name__)


class EnsembleGraph(SuperGraph):
    """
    TODO: Clean this up.
    SuperGraph that handles the ensemble processing.
    """

    def __init__(self, props={}, tag="", mode="process", supergraphs={}):
        # this stores the mapping for each run's data (i.e., Dataset)
        self.supergraphs = supergraphs

        super().__init__(props, tag, mode)

        # For each callsite we store the vector here.
        self.vector = {}

    def create_gf(self):
        """
        Create the graphframes for the ensemble operation.
        """
        # Set the gf as first of the dataset's gf
        if self.mode == "process":
            first_dataset = list(self.supergraphs.keys())[0]
            LOGGER.debug(f"Base for the union operation is: {first_dataset}")

            # TODO: do a deep copy.
            # Instead of a deep copy, create a new graphframe and return it.
            self.gf = self.supergraphs[first_dataset].gf
            self.gf.df = self.union_df()
            # There is no way to convert networkX to hatchet graph yet. So we are setting this to None.
            self.gf.graph = None
            self.gf.nxg = self.union_nxg()

            assert isinstance(self.gf, callflow.GraphFrame)

        elif self.mode == "render":
            path = os.path.join(self.dirname, self.tag)

            self.gf = callflow.GraphFrame()
            self.gf.read(path)

            #parameters = SuperGraph.read_parameters(path)   #TODO: where is this supposed to go?
            self.auxiliary_data = SuperGraph.read_auxiliary_data(path)

            #self.create_gf(data=data)
            #self.auxiliary_data = self.read_auxiliary_data()

            with self.timer.phase(f"Creating the data maps."):
                self.cct_df = self.gf.df[self.gf.df["name"].isin(self.gf.nxg.nodes())]
                self.create_ensemble_maps()
                for dataset in self.props["dataset_names"]:
                    self.create_target_maps(dataset)

    def union_df(self):
        """
        Union the dataframes.
        """
        df = pd.DataFrame([])
        for idx, tag in enumerate(self.supergraphs):
            gf = self.supergraphs[tag].gf

            df = pd.concat([df, gf.df], sort=True)

        assert isinstance(df, pd.DataFrame)
        return df

    def union_nxg(self):
        """
        Union the netwprkX graph.
        """
        nxg = nx.DiGraph()
        for idx, tag in enumerate(self.supergraphs):
            LOGGER.debug("-=========================-")
            LOGGER.debug(tag)
            self.union_nxg_recurse(nxg, self.supergraphs[tag].gf.nxg)

        return nxg

    # Return the union of graphs G and H.
    def union_nxg_recurse(self, nxg_1, nxg_2, name=None, rename=(None, None)):
        """
        Iterative concatenation of nodes from nxg_2 to nxg_1.
        """
        if not nxg_1.is_multigraph() == nxg_2.is_multigraph():
            raise nx.NetworkXError("G and H must both be graphs or multigraphs.")

        nxg_1.update(nxg_2)

        renamed_nodes = self.add_prefix(nxg_1, rename[1])

        is_same = set(nxg_1) == set(nxg_2)
        LOGGER.debug(f"Nodes in Graph 1 and Graph 2 are same? : {is_same}")
        if set(nxg_1) != set(nxg_2):
            LOGGER.debug(f"Difference is { list(set(nxg_1) - set(nxg_2))}")
            LOGGER.debug(f"Nodes in Graph 1: {set(nxg_1)}")
            LOGGER.debug(f"Nodes in Graph 2: {set(nxg_2)}")
        LOGGER.debug("-=========================-")

        if nxg_2.is_multigraph():
            new_edges = nxg_2.edges(keys=True, data=True)
        else:
            new_edges = nxg_2.edges(data=True)

        # add nodes and edges.
        nxg_1.add_nodes_from(nxg_2)
        nxg_1.add_edges_from(new_edges)

        # # add node attributes for each run
        # for n in renamed_nodes:
        #     self.add_node_attributes(nxg_1, n, name)

        return nxg_1

    # rename graph to obtain disjoint node labels
    def add_prefix(self, graph, prefix):
        if prefix is None:
            return graph

        def label(x):
            if is_string_like(x):
                name = prefix + x
            else:
                name = prefix + repr(x)
            return name

        return nx.relabel_nodes(graph, label)

    def add_edge_attributes(self):
        number_of_runs_mapping = self.number_of_runs()
        nx.set_edge_attributes(
            self.union, name="number_of_runs", values=number_of_runs_mapping
        )

    def number_of_runs(self):
        ret = {}
        for idx, name in enumerate(self.unionuns):
            for edge in self.unionuns[name].edges():
                if edge not in ret:
                    ret[edge] = 0
                ret[edge] += 1
        return ret

    def add_node_attributes(self, H, node, dataset_name):
        """
        TODO: Hoist this information to the df directly.
        """
        for idx, (key, val) in enumerate(H.nodes.items()):
            if dataset_name not in self.nxg.nodes[node]:
                self.nxg.nodes[node] = self.vector[node]
