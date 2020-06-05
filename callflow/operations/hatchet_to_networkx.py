import networkx as nx
import math
import json
from ast import literal_eval as make_tuple

import callflow

LOGGER = callflow.get_logger(__name__)
from callflow.utils import getNodeDictFromFrame, sanitizeName


class HatchetToNetworkX(nx.Graph):
    # Attributes:
    # 1. State => Pass the state which needs to be handled.
    # 2. path => '', 'path', 'group_path' or 'component_path'
    # 3. construct_graph -> To decide if we should construct graph from path
    # 4. add_data => To
    def __init__(
        self,
        gf,
        graph_type="entire",
        path_column_name="path",
    ):
        super(HatchetToNetworkX, self).__init__()
        self.path_column_name = path_column_name
        self.gf = gf

        self.nxg = nx.DiGraph()
        self.add_paths()

        self.adj_matrix = nx.adjacency_matrix(self.nxg)
        self.dense_adj_matrix = self.adj_matrix.todense()

        # TODO: Need to raise exception when the state.g is incorrect.
        # self.raiseExceptionIfNetworkXGraphIsIncorrect()

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

    def add_paths(self):
        graph = self.gf.graph

        for root in graph.roots:
            node_gen = root.traverse()

            root_dict = getNodeDictFromFrame(root.frame)
            root_name = root_dict["name"]
            root_paths = root.paths()
            node = root

            try:
                while node:
                    node_dict = getNodeDictFromFrame(node.frame)
                    node_name = node_dict["name"]

                    # Get all node paths from hatchet.
                    node_paths = node.paths()

                    #
                    for node_path in node_paths:
                        if len(node_path) >= 2:

                            source_node_dict = getNodeDictFromFrame(node_path[-2])
                            target_node_dict = getNodeDictFromFrame(node_path[-1])

                            if source_node_dict["line"] != "NA":
                                source_node_name = (
                                    sanitizeName(source_node_dict["name"])
                                    + ":"
                                    + str(source_node_dict["line"])
                                )
                            else:
                                source_node_name = sanitizeName(
                                    source_node_dict["name"]
                                )
                            if target_node_dict["line"] != "NA":
                                target_node_name = (
                                    sanitizeName(target_node_dict["name"])
                                    + ":"
                                    + str(target_node_dict["line"])
                                )
                            else:
                                target_node_name = sanitizeName(
                                    target_node_dict["name"]
                                )
                            self.nxg.add_edge(source_node_name, target_node_name)
                    node = next(node_gen)

            except StopIteration:
                pass
            finally:
                del root

    def raiseExceptionIfNetworkXGraphIsIncorrect(self):
        print(len(self.graph), len(self.nxg.nodes))
