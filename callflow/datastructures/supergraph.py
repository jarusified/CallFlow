# Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
# CallFlow Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

# ----------------------------------------------------------------------------
# Library imports
import os
import json
import copy
import pandas as pd
import numpy as np
import networkx as nx

# ----------------------------------------------------------------------------
# CallFlow imports
import callflow
from callflow.timer import Timer
from callflow.operations import Process, Group, Filter
from callflow.modules import EnsembleAuxiliary, SingleAuxiliary

LOGGER = callflow.get_logger(__name__)

# ----------------------------------------------------------------------------
class SuperGraph(object):
    """
    SuperGraph class to handle processing of a an input Dataset.
    """
    # --------------------------------------------------------------------------
    _FILENAMES = {"params": "env_params.txt", "aux": "auxiliary_data.json"}

    # --------------------------------------------------------------------------
    def __init__(self, props={}, tag="", mode="process"):
        """
        Arguments:
            props (dict): dictionary to store the configuration. CallFlow appends more information while processing.
            tag (str): Tag for each call graph.
            mode (str): process|render. process performs pre-processing, and render calculates layout for the client.
        """
        self.timer = Timer()

        self.props = props
        self.dirname = self.props["save_path"]
        self.tag = tag
        self.mode = mode

        self.create_gf()

    def create_gf(self):
        """Create a graphframe based on the mode.
        If mode is process, union operation is performed on the df and graph.
        If mode is render, corresponding files from .callflow/ensemble are read.
        """
        if self.mode == "process":
            self.gf = callflow.GraphFrame.from_config(self.props, self.tag)

        elif self.mode == "render":
            path = os.path.join(self.dirname, self.tag)

            self.gf = callflow.GraphFrame()
            self.gf.read(path)

            # Read only if "read_parameters" is specified in the config file.
            if self.props["read_parameter"]:
                self.parameters = SuperGraph.read_parameters(path)

            self.auxiliary_data = SuperGraph.read_auxiliary_data(path)

            # NOTE: I dont think we need this anymore. But keeping it just in case.
            # with self.timer.phase(f"Creating the data maps."):
            #     self.cct_df = self.gf.df[self.gf.df["name"].isin(self.gf.nxg.nodes())]
            #     self.create_ensemble_maps()
            #     for dataset in self.props["dataset_names"]:
            #         self.create_target_maps(dataset)

    # -------------------------------------------------------------------------
    # Question: Probably belongs to graphframe class?
    def get_module_name(self, callsite):
        """
        Get the module name for a callsite.
        Note: The module names can be specified using the config file.
        If such a mapping exists, this function returns the module based on mapping. Else, it queries the graphframe for a module name.

        Return:
            module name (str) - Returns the module name
        """
        if callsite in self.props["callsite_module_map"]:
            return self.props["callsite_module_map"][callsite]

        return self.gf.lookup_with_name(callsite)["module"].unique()[0]

    # -------------------------------------------------------------------------
    # Remove this block enitrely.
    def _remove__getter(self):
        """
        Getter for graphframe. Returns the graphframe.
        """
        return self.gf

    def _remove__setter(self, gf):
        """
        Setter for graphframe. Hooks the graphframe.
        """
        assert isinstance(gf, callflow.GraphFrame)

        self.gf = gf

    # ------------------------------------------------------------------------
    # The next block of functions attach the calculated result to the variable `gf`.
    def process_gf(self):
        """
        Process graphframe to add properties depending on the format.
        Current processing is supported for hpctoolkit and caliper.

        Note: Process class follows a builder pattern.
        (refer: https://en.wikipedia.org/wiki/Builder_pattern#:~:text=The%20builder%20pattern%20is%20a,Gang%20of%20Four%20design%20patterns.)
        """
        if self.props["format"][self.tag] == "hpctoolkit":

            process = (
                Process.Builder(self.gf, self.tag)
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
                Process.Builder(self.gf, self.tag)
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

        self.gf = process.gf

    def group_gf(self, group_by="module"):
        """
        Group the graphframe based on `group_by` parameter.
        """
        self.gf = Group(self.gf, group_by).gf

    def filter_gf(self, mode="single"):
        """
        Filter the graphframe.
        """
        self.gf = Filter(
            gf=self.gf,
            mode=mode,
            filter_by=self.props["filter_by"],
            filter_perc=self.props["filter_perc"],
        ).gf

    # ------------------------------------------------------------------------
    # Remove this block entirely.
    def _remove_read_gf(self, read_parameter=True, read_graph=False):
        """
        # Read a single dataset stored in .callflow directory.
        """
        LOGGER.info("Reading the dataset: {0}".format(self.tag))

        df_file_name = "df.csv"
        df_file_path = os.path.join(self.dirname, self.tag, df_file_name)
        df = pd.read_csv(df_file_path)
        if df.empty:
            raise ValueError(f"{df_file_path} is empty.")

        nxg_file_name = "nxg.json"
        nxg_file_path = os.path.join(self.dirname, self.tag, nxg_file_name)
        with open(nxg_file_path, "r") as nxg_file:
            graph = json.load(nxg_file)
        nxg = json_graph.node_link_graph(graph)
        assert nxg != None

        graph = {}
        if read_graph:
            graph_file_name = "hatchet_tree.txt"
            graph_file_path = os.path.join(self.dirname, self.tag, graph_file_name)
            with open(graph_file_path, "r") as graph_file:
                graph = json.load(graph_file)
            assert isinstance(graph, ht.GraphFrame.Graph)

        parameters = {}
        if read_parameter:
            parameters_filepath = os.path.join(self.dirname, self.tag, "env_params.txt")
            for line in open(parameters_filepath, "r"):
                s = 0
                for num in line.strip().split(","):
                    split_num = num.split("=")
                    parameters[split_num[0]] = split_num[1]

        return {"df": df, "nxg": nxg, "graph": graph, "parameters": parameters}

    def _remove_write_gf(self, write_df=True, write_graph=False, write_nxg=True):
        """
        # Write the dataset to .callflow directory.
        """
        # Get the save path.
        dirname = self.props["save_path"]

        gf = self.gf
        # dump the filtered dataframe to csv if write_df is true.
        if write_df:
            df_file_name = "df.csv"
            df_file_path = os.path.join(dirname, self.tag, df_file_name)
            gf.df.to_csv(df_file_path)

        if write_nxg:
            nxg_file_name = "nxg.json"
            nxg_file_path = os.path.join(dirname, self.tag, nxg_file_name)
            nxg_data = json_graph.node_link_data(self.gf.nxg)
            with open(nxg_file_path, "w") as nxg_file:
                json.dump(nxg_data, nxg_file)

        if write_graph:
            graph_filepath = os.path.join(dirname, self.tag, "hatchet_tree.txt")
            with open(graph_filepath, "a") as hatchet_graphFile:
                hatchet_graphFile.write(self.gf.tree(color=False))

    # ------------------------------------------------------------------------
    # Question: These functions just call another class, should we just call the corresponding classes directly?
    def write_gf(self, write_df=True, write_graph=False, write_nxg=True):
        path = os.path.join(self.props["save_path"], self.tag)
        self.gf.write(path, write_df, write_graph, write_nxg)

    def ensemble_auxiliary(self, datasets, MPIBinCount=20,
                                          RunBinCount=20, process=True, write=True):
        EnsembleAuxiliary(self.gf, datasets=datasets, props=self.props,
                                   MPIBinCount=MPIBinCount, RunBinCount=RunBinCount,
                                   process=process, write=write)

    def single_auxiliary(self, dataset="", binCount=20, process=True):
        SingleAuxiliary(self.gf, dataset=dataset, props=self.props,
                                 MPIBinCount=binCount, process=process)

    # ------------------------------------------------------------------------
    # Read/Write functions for parameter file, auxiliary information (for the client), and pair-wise similarity.
    @staticmethod
    def read_parameters(path):

        fname = os.path.join(path, SuperGraph._FILENAMES["params"])
        LOGGER.info(f"[Read] {fname}")

        parameters = None
        for line in open(fname, "r"):
            s = 0
            for num in line.strip().split(","):
                split_num = num.split("=")
                parameters[split_num[0]] = split_num[1]

        return parameters

    @staticmethod
    def read_auxiliary_data(path):

        fname = os.path.join(path, SuperGraph._FILENAMES["aux"])
        LOGGER.info(f"[Read] {fname}")
        data = None
        with open(fname, "r") as fptr:
            data = json.load(fptr)
        return data

    @staticmethod
    def _unused_write_similarity(datasets, states, type):
        """
        # Write the pair-wise graph similarities into .callflow directory.
        """
        assert False
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

    # -------------------------------------------------------------------------
    # NetworkX graph utility functions.
    # TODO: Remove this in the end.
    def remove_create_target_maps(self, dataset):
        # Reduce the entire_df to respective target dfs.
        self.target_df[dataset] = self.gf.df.loc[self.gf.df["dataset"] == dataset]

        # Unique modules in the target run
        self.target_modules[dataset] = self.target_df[dataset]["module"].unique()

        # Group the dataframe in two ways.
        # 1. by module
        # 2. by module and callsite
        self.target_module_group_df[dataset] = self.target_df[dataset].groupby(
            ["module"]
        )
        self.target_module_name_group_df[dataset] = self.target_df[dataset].groupby(
            ["module", "name"]
        )

        # Module map for target run {'module': [Array of callsites]}
        self.target_module_callsite_map[dataset] = (
            self.target_module_group_df[dataset]["name"].unique().to_dict()
        )

        # Inclusive time maps for the module level and callsite level.
        self.target_module_time_inc_map[dataset] = (
            self.target_module_group_df[dataset]["time (inc)"].max().to_dict()
        )
        self.target_name_time_inc_map[dataset] = (
            self.target_module_name_group_df[dataset]["time (inc)"].max().to_dict()
        )

        # Exclusive time maps for the module level and callsite level.
        self.target_module_time_exc_map[dataset] = (
            self.target_module_group_df[dataset]["time"].max().to_dict()
        )
        self.target_name_time_exc_map[dataset] = (
            self.target_module_name_group_df[dataset]["time"].max().to_dict()
        )

    def remove_create_ensemble_maps(self):
        self.modules = self.gf.df["module"].unique()

        self.module_name_group_df = self.gf.df.groupby(["module", "name"])
        self.module_group_df = self.gf.df.groupby(["module"])
        self.name_group_df = self.gf.df.groupby(["name"])

        # Module map for ensemble {'module': [Array of callsites]}
        self.module_callsite_map = self.module_group_df["name"].unique().to_dict()

        # Inclusive time maps for the module level and callsite level.
        self.module_time_inc_map = self.module_group_df["time (inc)"].max().to_dict()
        self.name_time_inc_map = self.module_name_group_df["time (inc)"].max().to_dict()

        # Exclusive time maps for the module level and callsite level.
        self.module_time_exc_map = self.module_group_df["time"].max().to_dict()
        self.name_time_exc_map = self.module_name_group_df["time"].max().to_dict()