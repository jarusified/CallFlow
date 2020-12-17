# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

class Snapshot:
    def __init__(self, graphs, indx1, indx2):
        """Initialize snapshot from a list of graphs.

            Keyword arguments:
            graphs -- list of networkX graphs 
            indx1 -- first index in the overall graph list
            indx2 -- last index in the overall graph list 
        """
        self.graphs = graphs[indx1:indx2]
        self.indx1 = indx1
        self.indx2 = indx2
        self.time1 = datetime.datetime.combine(self.graphs[0].graph['time'][0], datetime.time(self.graphs[0].graph['time'][1].item()))
        self.time2 = datetime.datetime.combine(self.graphs[-1].graph['time'][0], datetime.time(self.graphs[-1].graph['time'][1].item()))
        self.duration = self.time2 - self.time1
        self.union_g = None
        
        # occurences of nodes over time in a dict 
        nodes = []
        for g in self.graphs:
            nodes.append(g.nodes)
        # get number of occurences 
        self.node_occ = Counter(x for xs in nodes for x in set(xs))

    def __repr__(self):
        return 'Snapshot: ' + str(self.time1) + ' - ' + str(self.time2) 

    def __str__(self):
        return 'Snapshot: ' + str(self.time1) + ' - ' + str(self.time2) 
