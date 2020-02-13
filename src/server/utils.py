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

import os
import math
import fnmatch
from logger import log

# For converting graphml to json
import networkx as nx
from networkx.readwrite import json_graph
import json

def lookup(df, node):
    return df.loc[df["name"] == getNodeName(node)]

def lookup_with_name(df, name):
    return df.loc[df["name"] == name]

# Input : ./xxx/xxx/yyy
# # Output: yyy
# def sanitizeName(name):
#     if name == None or isinstance(name, float):
#         return "Unknown(NA)"
#     name_split = name.split("/")
#     return name_split[len(name_split) - 1]

def sanitizeName(name):
    print(name)
    if('/' in name):
        name_split = name.split("/")
        print(name_split[len(name_split) - 1])
        return name_split[len(name_split) - 1]
    else:
        return name

def avg(l):
    """uses floating-point division."""
    return sum(l) / float(len(l))

# Return the Callsite name from frame.
def getNodeDictFromFrame(frame):
    if frame["type"] == "function":
        return {"name": frame["name"], "line": "NA", "type": "function"}
    elif frame["type"] == "statement":
        return {"name": frame["file"], "line": frame["line"], "type": "statement"}
    elif frame['type'] == 'loop':
        return {"name": frame['file'], "line": frame["line"], "type": "loop"}

def getMaxIncTime(state):
    df = state.df
    ret = float(df["time (inc)"].max())
    return ret

# TODO: Get the maximum exclusive time from the graphframe.
def getMaxExcTime(state):
    df = state.df
    ret = float(df["time"].max())
    return ret

def getAvgIncTime(state):
    ret = 0.0
    graph = state.graph
    df = state.df
    for root in gf.graph.roots:
        ret += lookup(df, root)["time (inc)"].mean()
    return ret / len(gf.graph.roots)

def getAvgExcTime(state):
    df = state.df
    ret = df["time"].mean()
    return ret

def getMinIncTime(state):
    return 0

def getMinExcTime(state):
    return 0

def getNumOfNodes(state):
    df = state.df
    return df["module"].count()

def getNumbOfRanks(state):
    df = state.entire_df
    return len(df["rank"].unique())

def getMaxIncTime_from_gf(graph, dataframe):
    ret = 0.0
    for root in graph.roots:
        node_df = lookup(dataframe, root)
        ret = max(ret, float(max(node_df["time (inc)"].tolist())))
    return ret

def getMaxExcTime_from_gf(graph, dataframe):
    ret = float(dataframe["time"].max())
    return ret

def getAvgIncTime_from_gf(graph, dataframe):
    ret = 0.0
    for root in graph.roots:
        ret += lookup(dataframe, root)["time (inc)"].mean()
    return ret / len(graph.roots)

def getAvgExcTime_from_gf(graph, dataframe):
    ret = dataframe["time"].mean()
    return ret

def getMinIncTime_from_gf(graph, dataframe):
    return 0

def getMinExcTime_from_gf(graph, dataframe):
    return 0

def getNumOfNodes_from_gf(graph, dataframe):
    return dataframe["module"].count()

def getNumbOfRanks_from_gf(graph, dataframe):
    return len(dataframe["rank"].unique())

def graphmltojson(graphfile, outfile):
    """
	Converts GraphML file to json while adding communities/modularity groups
	using python-louvain. JSON output is usable with D3 force layout.
	"""
    G = nx.read_graphml(graphfile)

    # finds best community using louvain
    #    partition = community_louvain.best_partition(G)

    # adds partition/community number as attribute named 'modularitygroup'
    #    for n,d in G.nodes_iter(data=True):
    #        d['modularitygroup'] = partition[n]

    node_link = json_graph.node_link_data(G)
    json_data = json.dumps(node_link)

    # Write to file
    fo = open(outfile, "w")
    fo.write(json_data)
    fo.close()

def debug(action="", data={}):
    action = "[callfow.py] Action: {0}".format(action)
    if bool(data):
        data_string = "" + json.dumps(data, indent=4, sort_keys=True)
    else:
        data_string = ""
    log.debug(" {0} {1}".format(action, data_string))

def node_hash_mapper(df):
    ret = {}
    for idx, row in df.iterrows():
        df_node_index = str(row.nid)
        ret[df_node_index] = row.node
    return ret

def dfs(graph, dataframe, limit):
    def dfs_recurse(root, level):
        for node in root.children:
            result = ""
            if level < limit:
                for i in range(0, level):
                    result += "- "
                node_df = dataframe.loc[
                    (dataframe["nid"] == node.nid)
                    & (dataframe["name"] == node.callpath[-1])
                ]
                inclusive_runtime = " time (inc) = " + str(node_df["time (inc)"].mean())
                exclusive_runtime = " time = " + str(node_df["time"].mean())
                # module = "Module = " + str(node_df['module'].unique()[0])
                module = ""
                result += (
                    "Node = "
                    + node.callpath[-1]
                    + "["
                    + module
                    + ":"
                    + str(node.nid)
                    + "]"
                    + inclusive_runtime
                    + exclusive_runtime
                )
                log.info(result)
                level += 1
                dfs_recurse(node, level)

    level = 0
    for root in graph.roots:
        print("Root = {0} [{1}]".format("Root", root._hatchet_nid))
        dfs_recurse(root, level)

def getNodeCallpath(node):
    ret = []
    list_of_frames = list(node.path())
    for frame in list_of_frames:
        name = frame.get("name")
        if name != None:
            ret.append(frame.get("name"))
        else:
            ret.append(frame.get("file"))
    return ret

def getNodeParents(node):
    return node.parents

def getNodeName(node):
    name = node.frame.get("name")
    if name != None:
        return node.frame.get("name")
    else:
        return node.frame.get("file")

def convertStringToList(string):
    res = string.strip("][").split(", ")
    return res

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

def bfs_hatchet(graph):
    ret = {}
    node_count = 0
    roots = graph.roots
    for root in roots:
        node_gen = graph.roots[0].traverse()

        callpaths = root.paths()
        try:
            while callpaths != None:
                node_count += 1
                ret[root.callpath[-1]] = root.df_index
                root = next(node_gen)
        except StopIteration:
            pass
        finally:
            print("Total nodes in the graph", node_count)
            del root
            return ret

def framesToPathLists(paths):
    all_paths = []
    for path in paths:
        curr_path = []
        for frame in path:
            curr_path.append(frame['name'])
        all_paths.append(curr_path)
    return all_paths

def getPathListFromFrames(frames):
    paths = []
    for frame in frames:
        path = []
        for f in frame:
            if f['type'] == 'function':
                path.append(f['name'])
            elif f['type'] == 'statement':
                path.append(f['file'])
            elif f['type'] == 'loop':
                path.append(f['file'])
        paths.append(path)
    return path