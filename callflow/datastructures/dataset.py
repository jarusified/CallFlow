import os

# from hatchet import *

from callflow import GraphFrame


class Dataset(object):

    # TODO: Assign self.g, self.root...
    def __init__(self, dataset_name):

        # it appears we're using name as "union", "filter", etc.
        # this is not a data set name!
        self.name = dataset_name

        # instead of the old variables, we will use these new ones.
        # these are callflow.graphframe object (has gf, df, and networkx)
        self.gf = None
        self.entire_gf = None

        
        self.projection_data = {}

    """
    def lookup_by_column(self, _hash, col_name):
        # dont think this is used anywhere
        assert False

        ret = []
        node_df = self.df.loc[self.df["node"] == self.map[str(_hash)]]
        node_df_T = node_df.T.squeeze()
        node_df_T_attr = node_df_T.loc[col_name]
        if node_df_T_attr is not None:
            if type(node_df_T_attr) is str or type(node_df_T_attr) is float:
                ret.append(node_df_T_attr)
            else:
                ret = node_df_T_attr.tolist()
        return ret
    """

    def lookup(self, node):
        return self.new_gf.lookup(node)
        # return self.df.loc[
        #    (self.df["name"] == node.callpath[-1]) & (self.df["nid"] == node.nid)
        # ]

    def lookup_with_node(self, node):
        return self.new_gf.lookup_with_node(node)
        # return self.df.loc[self.df["name"] == node.callpath[-1]]

    def lookup_with_name(self, name):
        return self.new_gf.lookup_with_name(node)
        # return self.df.loc[self.df["name"] == name]

    def lookup_with_vis_nodeName(self, name):
        return self.new_gf.lookup_with_name(node)
        # return self.df.loc[self.df["vis_node_name"] == name]

    def update_df(self, col_name, mapping):
        return self.new_gf.update_df(col_name, mapping)
        """
        self.df[col_name] = self.df["name"].apply(
            lambda node: mapping[node] if node in mapping.keys() else ""
        )
        """

    def grouped_df(self, attr):
        self.gdf[attr] = self.new_gf.df.groupby(attr, as_index=True, squeeze=True)
        self.gdfKeys = self.gdf[attr].groups.keys()



    @staticmethod
    def create_target_maps(df):
        """
        """
        self.target_df = {}
        self.target_modules = {}
        self.target_module_group_df = {}
        self.target_module_name_group_df = {}
        self.target_module_callsite_map = {}
        self.target_module_time_inc_map = {}
        self.target_module_time_exc_map = {}
        self.target_name_time_inc_map = {}
        self.target_name_time_exc_map = {}

        for run in self.props["dataset_names"]:
            # Reduce the entire_df to respective target dfs.
            self.target_df[run] = df.loc[df["dataset"] == run]

            # Unique modules in the target run
            self.target_modules[run] = self.target_df[run]["module"].unique()

            # Group the dataframe in two ways.
            # 1. by module
            # 2. by module and callsite
            self.target_module_group_df[run] = self.target_df[run].groupby(["module"])
            self.target_module_name_group_df[run] = self.target_df[run].groupby(
                ["name"]
            )

            # Module map for target run {'module': [Array of callsites]}
            self.target_module_callsite_map[run] = self.target_module_group_df[run][
                "name"
            ].unique()

            # Inclusive time maps for the module level and callsite level.
            self.target_module_time_inc_map[run] = (
                self.target_module_group_df[run]["time (inc)"].max().to_dict()
            )
            self.target_name_time_inc_map[run] = (
                self.target_module_name_group_df[run]["time (inc)"].max().to_dict()
            )

            # Exclusive time maps for the module level and callsite level.
            self.target_module_time_exc_map[run] = (
                self.target_module_group_df[run]["time"].max().to_dict()
            )
            self.target_name_time_exc_map[run] = (
                self.target_module_name_group_df[run]["time"].max().to_dict()
            )

    def create_ensemble_maps(self):
        """
        """
        self.modules = self.new_gf.df["module"].unique()

        self.module_name_group_df = df.groupby(["module", "name"])
        self.module_group_df = df.groupby(["module"])

        # Module map for ensemble {'module': [Array of callsites]}
        self.module_callsite_map = df["name"].unique()

        # Inclusive time maps for the module level and callsite level.
        self.module_time_inc_map = self.module_group_df["time (inc)"].max().to_dict()
        self.name_time_inc_map = self.module_name_group_df["time (inc)"].max().to_dict()

        # Exclusive time maps for the module level and callsite level.
        self.module_time_exc_map = self.module_group_df["time"].max().to_dict()
        self.name_time_exc_map = self.module_name_group_df["time"].max().to_dict()


    def get_top_n_callsites_by_attr(self, count, sort_attr):
        """
        """
        xgroup_df = self.entire_df.groupby(["name"]).mean()
        sort_xgroup_df = xgroup_df.sort_values(by=[sort_attr], ascending=False)
        callsites_df = sort_xgroup_df.nlargest(count, sort_attr)
        return callsites_df.index.values.tolist()