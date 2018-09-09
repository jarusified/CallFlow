##############################################################################
# Copyright (c) 2018-2019, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Callflowt.
# Created by Suraj Kesavan <kesavan1@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# For details, see: https://github.com/LLNL/Callflow
# Please also read the LICENSE file for the MIT License notice.
##############################################################################

#!/usr/bin/env python3

import utils

# Preprocess the dataframe
# Builder object
# Preprocess.add_X().add_Y().....
class PreProcess():
    def __init__(self, builder):
        self.graph = builder.graph
        self.df = builder.df
        self.map = builder.map
        
    def map(self):
        return self.map

    class Builder(object):
        def __init__(self, state):
            self.state = state
            self.df = state.df
            self.graph = state.graph
            self.map = {}
            
        def build(self):
            return PreProcess(self)

        # Add the path information from the node object
        def add_path(self):
            self.df['path'] = self.df['node'].apply(lambda node: node.callpath)

            return self

        def add_incTime(self):
            ret = {}
            for idx, row in self.df.iterrows():
                ret[str(row.node.df_index)] = self.state.lookup(row.node.df_index)['CPUTIME (usec) (I)'].tolist()

            self.map['incTime'] = ret
            return self

        def add_excTime(self):
            ret = {}
            for idx, row in self.df.iterrows():
                ret[str(row.node.df_index)] = self.state.lookup(row.node.df_index)['CPUTIME (usec) (E)'].tolist()

            self.map['excTime'] = ret
            return self

        # Max of the inclusive Runtimes among all processes
        # node -> max([ inclusive times of process])
        def add_max_incTime(self):
            ret = {}

            for idx, row in self.df.iterrows():
                ret[str(row.node.df_index)] = max(self.state.lookup(row.node.df_index)['CPUTIME (usec) (I)'])

            self.map['max_incTime'] = ret
            self.df['max_incTime'] = self.df['node'].apply(lambda node: self.map['max_incTime'][str(node.df_index)])
            return self

        # Avg of inclusive Runtimes among all processes
        # node -> avg([ inclusive times of process])
        def add_avg_incTime(self):
            ret = {}

            for idx, row in self.df.iterrows():
                ret[str(row.node.df_index)] = utils.avg(self.state.lookup(row.node.df_index)['CPUTIME (usec) (I)'])

            self.map['avg_incTime'] = ret    
            self.df['avg_incTime'] = self.df['node'].apply(lambda node: self.map['avg_incTime'][str(node.df_index)])

            return self
        
        # Imbalance percentage Series in the dataframe    
        def add_imbalance_perc(self):
            ret = {}
            
            for idx, row in self.df.iterrows():
                ret[str(row.node.df_index)] = (self.map['max_incTime'][str(row.node.df_index)] - self.map['avg_incTime'][str(row.node.df_index)])/ self.map['max_incTime'][str(row.node.df_index)]

            self.map['imbalance_perc'] = ret
            self.df['imbalance_perc'] = self.df['node'].apply(lambda node: self.map['imbalance_perc'][str(node.df_index)])
            return self
            
        def add_callers_and_callees(self):
            graph = self.graph
            callees = {}
            callers = {}
            
            root = graph.roots[0]
            node_gen = graph.roots[0].traverse()
            callers[root] = []
            callees[root] = []
        
            try:
                while root.callpath != None:
                    root = next(node_gen)
                    if root.parent not in callees:
                        callees[root.parent] = []
                    
                    callees[root.parent].append(root.df_index)
            except StopIteration:
                pass
            finally:
                del root

#            self.map['callees'] = callees
            self.df['callees'] = self.df['node'].apply(lambda node: callees[node] if node in callees else [])            

            return self
        
        def add_show_node(self):
            self.map['show_node'] = {}
            self.df['show_node'] = self.df['node'].apply(lambda node: True)

            return self

        def update_show_node(self, show_node_map):
            self.map.show_node = show_node_map
            self.df['show_node'] = self.df['node'].apply(lambda node: show_node_map[str(node.df_index)])

        # node_name is different from name in dataframe. So creating a copy of it.
        def add_vis_node_name(self):
            self.df['vis_node_name'] = self.df['name'].apply(lambda name: name)

            return self

        def update_node_name(self, node_name_map):
            self.df['node_name'] = self.df['name'].apply(lambda name: node_name_map[name])

        def update_module_name(self):
            self.df['module'] = self.df['module'].apply(lambda name: utils.sanitizeName(name))
            return self
        

        def add_df_index(self):
            self.df['df_index'] = self.df['node'].apply(lambda node: node.df_index)           
            return self

        