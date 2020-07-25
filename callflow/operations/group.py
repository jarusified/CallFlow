# *******************************************************************************
# * Copyright (c) 2020, Lawrence Livermore National Security, LLC.
# * Produced at the Lawrence Livermore National Laboratory.
# *
# * Written by Suraj Kesavan <htpnguyen@ucdavis.edu>.
# *
# * LLNL-CODE-740862. All rights reserved.
# *
# * This file is part of CallFlow. For details, see:
# * https://github.com/LLNL/CallFlow
# * Please also read the LICENSE file for the MIT License notice.
# ******************************************************************************
# Library imports
import pandas as pd
import time
import networkx as nx
from ast import literal_eval as make_list

# CallFlow imports
import callflow

LOGGER = callflow.get_logger(__name__)


class Group:
    """
    Group operation on the CallFlow SuperGraph.
    1. Loops on the callflow.SuperGraph.nxg and decomposes the path to 
    perform path decomposition at different levels of granularity. 
    2. Currently, two kinds of granularity is considered 
        a. Module level callgraph.
        b. CCT hierarchy inside a Module.
    3. The collected information on the granularities are added back to 
    the Hatchet's GraphFrame.
    4. The following columns are appended to the DataFrame.
        a. group_path
        b. component_path
        c. component_level
        d. is_entry
    """

    def __init__(self, gf, group_by="name"):
        assert isinstance(gf, callflow.GraphFrame)
        # Set self.gf, the groupby operation needs the graphframe.
        self.gf = gf

        # Check if there is a column in df, group_by.
        assert group_by in self.gf.df.columns
        self.group_by = group_by

        # Computes performs the path decomposition on the SuperGraph.
        self.compute(gf, group_by)

    @staticmethod
    # TODO: We need to traverse the graph. Not just consider the edges. 
    def compute(gf, group_by):
        group_path = {}
        component_path = {}
        component_level = {}
        entry_func = {}
        show_node = {}
        module = {}

        callsite_group_dict = gf.df.set_index("name")[group_by].to_dict()

        for idx, edge in enumerate(gf.nxg.edges()):
            """
            Performs path decomposition on edge
            """
            snode = edge[0]
            tnode = edge[1]

            # TODO: Need to move this to utils.
            if "/" in snode:
                snode = snode.split("/")[-1]
            if "/" in tnode:
                tnode = tnode.split("/")[-1]

            spath = callsite_group_dict[snode]
            tpath = callsite_group_dict[tnode]
            
            # Set the group_path. 
            group_path[snode] = Group._create_group_path(spath)
            group_path[tnode] = Group._create_group_path(tpath)

            # Set the component_path.
            component_path[snode] = Group._create_component_path(spath, group_path[snode])        
            component_path[tnode] = Group._create_component_path(tpath, group_path[tnode])

            # TODO: Remove this. We can calculate the len in the client.
            component_level[snode] = len(component_path[snode])
            component_level[tnode] = len(component_path[tnode])

            if component_level[snode] == 2:
                entry_func[snode] = True
            else:
                entry_func[snode] = False

            if component_level[tnode] == 2:
                is_entry[tnode] = True
            else:
                is_entry[tnode] = False

        self.update_df("group_path", group_path)
        self.update_df("component_path", component_path)
        self.update_df("component_level", component_level)
        self.update_df("entry_function", entry_func)

    @staticmethod
    def _create_group_path(path):
        if isinstance(path, str):
            path = make_list(path)
        group_path = []
        prev_module = None
        for idx, callsite in enumerate(path):
            if idx == 0:
                # Assign the first callsite as from_callsite and not push into an array.
                from_callsite = callsite
                from_module = self.callsite_module_map[from_callsite]

                # Store the previous module to check the hierarchy later.
                prev_module = from_module

                # Create the entry function and other functions dict.
                if from_module not in self.entry_funcs:
                    self.entry_funcs[from_module] = []
                if from_module not in self.other_funcs:
                    self.other_funcs[from_module] = []

                # Push into entry function dict since it is the first callsite.
                self.entry_funcs[from_module].append(from_callsite)

                # Append to the group path.
                group_path.append(from_module + "=" + from_callsite)

            elif idx == len(path) - 1:
                # Final callsite in the path.
                to_callsite = callsite
                if "/" in to_callsite:
                    to_callsite = to_callsite.split("/")[-1]

                to_module = self.callsite_module_map[to_callsite]

                if prev_module != to_module:
                    group_path.append(to_module + "=" + to_callsite)

                if to_module not in self.entry_funcs:
                    self.entry_funcs[to_module] = []
                if to_module not in self.other_funcs:
                    self.other_funcs[to_module] = []

                if to_callsite not in self.other_funcs[to_module]:
                    self.other_funcs[to_module].append(to_callsite)

                if to_callsite not in self.entry_funcs[to_module]:
                    self.entry_funcs[to_module].append(to_callsite)
            else:
                # Assign the from and to callsite.
                from_callsite = path[idx - 1]
                if "/" in callsite:
                    to_callsite = callsite.split("/")[-1]
                else:
                    to_callsite = callsite

                from_module = self.callsite_module_map[from_callsite]
                to_module = self.callsite_module_map[to_callsite]

                # Create the entry function and other function dict if not already present.
                if to_module not in self.entry_funcs:
                    self.entry_funcs[to_module] = []
                if to_module not in self.other_funcs:
                    self.other_funcs[to_module] = []

                # if previous module is not same as the current module.
                if to_module != prev_module:
                    # TODO: Come back and check if it is in the path.
                    if to_module in group_path:
                        prev_module = to_module
                    else:
                        group_path.append(to_module + "=" + to_callsite)
                        prev_module = to_module
                        if to_callsite not in self.entry_funcs[to_module]:
                            self.entry_funcs[to_module].append(to_callsite)

                elif to_module == prev_module:
                    to_callsite = callsite
                    # to_module = self.entire_df.loc[self.entire_df['name'] == to_callsite]['module'].unique()[0]
                    to_module = self.callsite_module_map[to_callsite]

                    prev_module = to_module

                    if to_callsite not in self.other_funcs[to_module]:
                        self.other_funcs[to_module].append(to_callsite)

        return group_path

    @staticmethod
    def _clean_node_name(node):
        return node.split("/")[-1]
        

    @staticmethod
    def _create_component_path(self, path, group_path):
        """
        
        """
        assert isinstance(path, list)
        assert isinstance(group_path, list)

        callsite_module_map = self.gf.df.set_index("name")[group_by].to_dict()

        component_path = []
        component_module = group_path[len(group_path) - 1].split("=")[0]

        for idx, node in enumerate(path):
            node = Group._clean_node_name(node)
            module = self.callsite_module_map[node]
            if component_module == module:
                component_path.append(node_func)

        component_path.insert(0, component_module)
        return tuple(component_path)

    # TODO: Move to utils folder.
    def _append_column_to_dataframe(self, col_name, mapped_dict):
        """
        Update the dataframe with the mapped_dict
        """
        self.gf.df[col_name] = self.gf.df["name"].apply(
            lambda node: mapped_dict[node] if node in mapped_dict.keys() else ""
        )
