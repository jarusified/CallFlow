import networkx as nx
import pandas as pd
import callflow
from callflow import GraphFrame, Dataset
LOGGER = callflow.get_logger(__name__)


# Mostly derive from supergraph.
# Should contain the vector that stores the properties as explained in paper. 
# should contain a function `create` which contains the 
class UnionGraph(Dataset):
    def __init__(self, props, tag, datasets):
        super().__init__(props, tag)
        self.nxg = nx.DiGraph()
        self.df = pd.DataFrame([])
        self.entire_gf = GraphFrame(graph=None, dataframe=self.df)
        self.gf = None
        self.datasets = datasets

    def _getter(self):
        pass

    def _setter(self):
        pass

    def union(self, gf_type="entire"):
        for idx, dataset in enumerate(self.datasets):
            self.unionize(self.datasets[dataset].gf)
            self.entire_gf.df = pd.concat([self.df, self.datasets[dataset].gf.df], sort=True)

        self.entire_gf.nxg = self.nxg
        return self.entire_gf

    # Return the union of graphs G and H.
    def unionize(self, gf, name=None, rename=(None, None)):
        if not self.nxg.is_multigraph() == gf.nxg.is_multigraph():
            raise nx.NetworkXError("G and H must both be graphs or multigraphs.")

        self.nxg.update(gf.nxg)

        renamed_nodes = self.add_prefix(gf.nxg, rename[1])

        LOGGER.debug("-=========================-")
        is_same = set(self.nxg) == set(gf.nxg)
        LOGGER.debug(f"Nodes in R and H are same? : {is_same}")
        if set(self.nxg) != set(gf.nxg):
            LOGGER.debug(f"Difference is { list(set(gf.nxg) - set(self.nxg))}")
            LOGGER.debug(f"Nodes in R: {set(self.nxg)}")
            LOGGER.debug(f"Nodes in H: {set(gf.nxg)}")
        LOGGER.debug("-=========================-")

        if gf.nxg.is_multigraph():
            new_edges = gf.nxg.edges(keys=True, data=True)
        else:
            new_edges = gf.nxg.edges(data=True)

        # add nodes and edges.
        self.nxg.add_nodes_from(gf.nxg)
        self.nxg.add_edges_from(new_edges)

        # add node attributes for each run
        for n in renamed_nodes:
            self.add_node_attributes(gf.nxg, n, name)

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
        for idx, (key, val) in enumerate(H.nodes.items()):
            if dataset_name not in self.nxg.nodes[node]:
                self.nxg.nodes[node][dataset_name] = 0
            if key == node:
                self.nxg.nodes[node][dataset_name] = 1