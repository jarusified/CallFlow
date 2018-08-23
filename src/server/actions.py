##############################################################################
# Copyright (c) 2018-2019, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Callflow.
# Created by Suraj Kesavan <kesavan1@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# For details, see: https://github.com/LLNL/Callflow
# Please also read the LICENSE file for the MIT License notice.
##############################################################################

#!/usr/bin/env python3

import utils


def groupBy(gf, attr):
    graph = gf.graph
    df = gf.dataframe
    
    groupsTracked = {}
    
    root = graph.roots[0]
    node_gen = graph.roots[0].traverse()

    group_path_map = {}
    show_node_map = {}
    node_name_map = {}
    
    # convert to pandas group dataframe
    gdf = df.groupby(attr, as_index=True, squeeze=True)  
    gdfKeys = gdf.groups.keys()
    
    rootdf = utils.lookup(df, root)
    group_path_map[rootdf.node[0]] = tuple(['<program root>'])
    node_name_map[rootdf.node[0]] = '<program root>'
    show_node_map[rootdf.node[0]] = True
    try:
        while root.callpath != None:
            root = next(node_gen)                
            target = utils.lookup(df, root)
            source = utils.lookup(df, root.parent)
            if not target.empty and not source.empty:
                group_path_map[target.node[0]] = create_group_path(df, source.path[0])
                
                if target.module.isin(groupsTracked)[0]:
                    show_node_map[target.node[0]] = False
                    node_name_map[target.node[0]] = ''
                else:
                    show_node_map[target.node[0]] = True
                    if len(utils.lookupByAttr(df, target.node[0], attr)) != 0 :
                        node_name_map[target.node[0]] = utils.sanitizeName(utils.lookupByAttr(df, target.node[0], attr)[0])
                    else:
                        node_name_map[target.node[0]] = ''
                    groupsTracked[target.module[0]] = True
    except StopIteration:
        pass
    finally:
        del root

    utils.update_df(df, 'group_path', group_path_map)
    utils.update_df(df, 'show_node', show_node_map)
    utils.update_df(df, 'node_name', node_name_map)

    print node_name_map
    return gf

def create_group_path(df, path):
    group_path = ['<program root>']
    temp = None
    for i, elem in enumerate(path):
        module = utils.lookupByName(df, elem).module[0]
        sanitize_module = utils.sanitizeName(module)
        if temp == None or sanitize_module != temp:
            group_path.append(sanitize_module)
            temp = sanitize_module
    return tuple(group_path)
