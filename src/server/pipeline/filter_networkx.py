import numpy as np
import networkx as nx
from utils.logger import log


class FilterNetworkX:
    def __init__(self, state):
        self.df = state.df
        self.dataset_df = self.df.groupby(["dataset"])
        self.dataset_idx = {}
        self.set_max_min_times()

    def set_max_min_times(self):
        self.max_time_inc_list = np.array([])
        self.min_time_inc_list = np.array([])
        self.max_time_exc_list = np.array([])
        self.min_time_exc_list = np.array([])
        count = 0
        for dataset, df in self.dataset_df:
            self.dataset_idx[dataset] = count
            self.max_time_inc_list = np.hstack(
                [self.max_time_inc_list, df["time (inc)"].max()]
            )
            self.min_time_inc_list = np.hstack(
                [self.min_time_inc_list, df["time (inc)"].min()]
            )
            self.max_time_exc_list = np.hstack(
                [self.max_time_exc_list, df["time"].max()]
            )
            self.min_time_exc_list = np.hstack(
                [self.min_time_exc_list, df["time"].min()]
            )
            count += 1
        print("Dataset idx: ", self.dataset_idx)
        print("Min. time (inc): ", self.min_time_inc_list)
        print("Max. time (inc): ", self.max_time_inc_list)
        print("Min. time (exc): ", self.min_time_exc_list)
        print("Max. time (exc): ", self.max_time_exc_list)
        self.max_time_inc = np.max(self.max_time_inc_list)
        self.min_time_inc = np.min(self.min_time_inc_list)
        self.max_time_exc = np.max(self.max_time_exc_list)
        self.min_time_exc = np.min(self.min_time_exc_list)

    def filter_df_by_time_inc(self, perc):
        log.debug(f"[Filter] By Inclusive time : {perc}")
        df = self.df.loc[(self.df["time (inc)"] > perc * 0.01 * self.max_time_inc)]
        filter_call_sites = df["name"].unique()
        return df[df["name"].isin(filter_call_sites)]

    def filter_df_by_time(self, perc):
        log.debug(f"[Filter] By Exclusive time : {perc}")
        # df = self.df.loc[self.df['time'] > perc * 0.01 * self.max_time_exc]
        df = self.df.loc[self.df['time'] > perc]
        filter_call_sites = df["name"].unique()
        print(filter_call_sites)
        return df[df["name"].isin(filter_call_sites)]

    def filter_graph_by_time_inc(self, df, g):
        callsites = df["name"].unique()

        ret = nx.DiGraph()

        for edge in g.edges():
            # If source is present in the callsites list
            if(edge[0] in callsites and edge[1] in callsites):
                ret.add_edge(edge[0], edge[1])
            else:
                log.info(f"Removing the edge: {edge}")

        return ret

    # Refer https://stackoverflow.com/questions/28095646/finding-all-paths-walks-of-given-length-in-a-networkx-graph
    def findPaths(self, g, u, n,excludeSet = None):
        if excludeSet == None:
            excludeSet = set([u])
        else:
            excludeSet.add(u)
        if n == 0:
            return [[u]]

        print("Callsite: ", u)
        for neighbor in g.neighbors(u):
            print(neighbor)
        # print("neighbors: ", g.neighbors(u))
        paths = [[].append(path) for neighbor in g.neighbors(u) if neighbor not in excludeSet for path in self.findPaths(g, neighbor, n-1, excludeSet)]
        excludeSet.remove(u)
        return paths

    def filter_graph_by_time(self, df, g):
        callsites = df["name"].unique()

        ret = nx.DiGraph()

        for callsite in callsites:
            path = df.loc[df['name'] == callsite]['path'].tolist()[0]
            # print(self.findPaths(g, callsite, 10))
            ret.add_path(path)

        return ret


