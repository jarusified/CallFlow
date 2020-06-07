import os
import json
import pandas as pd
import hatchet as ht
from networkx.readwrite import json_graph

import callflow
from callflow import GraphFrame
from callflow.operations import Process, Group, Filter

LOGGER = callflow.get_logger(__name__)


class Dataset(object):
    def __init__(self, props={}, tag=""):

        # it appears we're using name as "union", "filter", etc.
        # this is not a data set name!
        self.tag = tag
        self.props = props

        # instead of the old variables, we will use these new ones.
        # these are callflow.graphframe object (has gf, df, and networkx)
        self.gf = None
        self.entire_gf = None

        print(self.props)
        self.dirname = self.props["save_path"]

        self.callsite_module_map = {}
        self.projection_data = {}

    def _getter(self, gf_type):
        """
        Getter for graphframe. Returns the graphframe based on `gf_type`.
        """
        if gf_type == "filter":
            gf = self.gf
        elif gf_type == "entire":
            gf = self.entire_gf

        return gf

    def _setter(self, gf, gf_type):
        """
        Setter for graphframe. Hooks the graphframe based on `gf_type`.
        """
        assert isinstance(gf, ht.GraphFrame)

        if gf_type == "filter":
            self.gf = gf
        elif gf_type == "entire":
            self.entire_gf = gf

    def create_gf(self):
        """
        Creates a graphframe using config and networkX grapg from hatchet graph.
        Each graphframe is tagged by a unique identifier. 
        e.g., here is the runName from config file or JSON.

        """
        self.entire_gf = GraphFrame.from_config(self.props, self.tag)
        self.nxg = GraphFrame.from_hatchet_graph(self.entire_gf.graph)

    def process_gf(self, gf_type):
        """
        # TODO: move the process functions to graphframe. 
        # I am not doing this now. Might be next commit. 
        Process graphframe to add properties depending on the format. 
        Current processing is supported for hpctoolkit and caliper. 
        """
        gf = self._getter(gf_type)
        if self.props["format"][self.tag] == "hpctoolkit":
            process = (
                Process.Builder(gf, self.tag)
                .add_path()
                .create_name_module_map()
                .add_callers_and_callees()
                .add_dataset_name()
                .add_imbalance_perc()
                .add_module_name_hpctoolkit()
                .add_vis_node_name()
                .build()
            )
        elif self.props["format"][self.tag] == "caliper_json":
            process = (
                Process.Builder(gf, self.tag)
                .add_time_columns()
                .add_rank_column()
                .add_callers_and_callees()
                .add_dataset_name()
                .add_imbalance_perc()
                .add_module_name_caliper(self.props["callsite_module_map"])
                .create_name_module_map()
                .add_vis_node_name()
                .add_path()
                .build()
            )

        self._setter(process.gf, "entire")

    def group_gf(self, gf_type="entire", group_by="module"):
        """
        Group the graphframe based on `group_by` parameter. 
        """
        gf = self._getter(gf_type)
        group = Group(gf, group_by)
        self._setter(group.gf, gf_type)
        assert isinstance(gf, callflow.GraphFrame)


    def filter_gf(self, mode="single"):
        """
        Filter the graphframe. 
        """
        gf = self.entire_gf
        filter_res = Filter(
            gf,
            mode=mode,
            filter_by=self.props["filter_by"],
            filter_perc=self.props["filter_perc"],
        )
        self.gf = filter_res.gf
        assert isinstance(gf, callflow.GraphFrame)

        self.gf = filter_res.gf

    def target_maps(self):
        """
        Create target maps. 
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

    def ensemble_maps(self):
        """
        """
        self.modules = self.new_gf.df["module"].unique()

        self.module_name_group_df = self.new_gf.df.groupby(["module", "name"])
        self.module_group_df = self.new_gf.df.groupby(["module"])

        # Module map for ensemble {'module': [Array of callsites]}
        self.module_callsite_map = self.new_gf.df["name"].unique()

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

    def read_dataset(
        self, gf_type="entire", read_df=True, read_nxg=True, read_parameters=True
    ):
        """
        # Read a single dataset stored in .callflow directory.
        """

        LOGGER.info("Reading the dataset: {0}".format(self.tag))

        if read_df:
            df_file_name = gf_type + "_df.csv"
            df_file_path = os.path.join(self.dirname, self.tag, df_file_name)
            self.gf = GraphFrame()
            df = pd.read_csv(df_file_path)

            if df.empty:
                raise ValueError(f"{df_file_path} is empty.")

            self.gf.df = df

        if read_nxg:
            nxg_file_name = gf_type + "_nxg.json"
            nxg_file_path = os.path.join(self.dirname, self.tag, nxg_file_name)
            with open(nxg_file_path, "r") as nxg_file:
                graph = json.load(nxg_file)
            nxg = json_graph.node_link_graph(graph)

            assert nxg != None

            self.gf.nxg = nxg

        if read_parameters:
            parameters_filepath = os.path.join(self.dirname, self.tag, "env_params.txt")
            projection_data = {}
            for line in open(parameters_filepath, "r"):
                s = 0
                for num in line.strip().split(","):
                    split_num = num.split("=")
                    projection_data[split_num[0]] = split_num[1]

            assert projection_data != {}

            self.projection_data = projection_data

    def write_dataset(self, gf_type, write_df=True, write_graph=True, write_nxg=True):
        """
        # Write the dataset to .callflow directory.
        """
        # Get the save path.
        dirname = self.props["save_path"]

        gf = self._getter(gf_type)

        # dump the filtered dataframe to csv if write_df is true.
        if write_df:
            df_file_name = gf_type + "_df.csv"
            df_file_path = os.path.join(dirname, self.tag, df_file_name)
            gf.df.to_csv(df_file_path)

        #
        if write_nxg:
            nxg_file_name = gf_type + "_nxg.json"
            nxg_file_path = os.path.join(dirname, self.tag, nxg_file_name)
            nxg_data = json_graph.node_link_data(gf.nxg)
            with open(nxg_file_path, "w") as nxg_file:
                json.dump(nxg_data, nxg_file)

        if write_graph:
            graph_filepath = os.path.join(dirname, self.tag, "hatchet_tree.txt")
            with open(graph_filepath, "a") as hatchet_graphFile:
                hatchet_graphFile.write(gf.tree(color=False))

    def writeSimilarity(self, datasets, states, type):
        """
        # Write the pair-wise graph similarities into .callflow directory.
        """
        ret = {}
        for idx, dataset in enumerate(datasets):
            ret[dataset] = []
            for idx_2, dataset2 in enumerate(datasets):
                union_similarity = Similarity(states[dataset2].g, states[dataset].g)
                ret[dataset].append(union_similarity.result)

        dirname = self.config.callflow_dir
        name = self.config.runName
        # similarity_filepath = dirname + "/" + "similarity.json"
        similarity_filepath = os.path.join(dirname, "similarity.json")
        with open(similarity_filepath, "w") as json_file:
            json.dump(ret, json_file)

    def read_auxiliary_data(self):
        """
        # Read the auxiliary data from all_data.json. 
        """
        all_data_filepath = os.path.join(self.config.save_path, "all_data.json")
        LOGGER.info(f"[Read] {all_data_filepath}")
        with open(all_data_filepath, "r") as filter_graphFile:
            data = json.load(filter_graphFile)
        return data
