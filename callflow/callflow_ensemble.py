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

import time
import json
import pandas as pd

import callflow

LOGGER = callflow.get_logger(__name__)
from callflow.pipeline import Pipeline
from callflow import Dataset

from callflow.utils import getMaxExcTime, getMinExcTime, getMaxIncTime, getMinIncTime
from callflow.timer import Timer
from callflow import CCT, SuperGraph, BaseCallFlow
from callflow.modules import (
    RankHistogram,
    EnsembleAuxiliary,
    Gradients,
    ModuleHierarchy,
    ParameterProjection,
    DiffView,
)
from callflow.algorithms import DeltaConSimilarity

# Create states for each dataset.
# Note: gf would never change from create_gf.
# # Note: fgf would be changed when filter props are changed by client.
# Note: df is always updated.
# Note: graph is always updated.
class EnsembleCallFlow(BaseCallFlow):
    def __init__(self, config=None, process=None):
        super(EnsembleCallFlow, self).__init__(config, process)

# Config contains properties set by the input config file.
        self.currentMPIBinCount = 20
        self.currentRunBinCount = 20

        # TODO: should go in appstate
        # self.target_df = {}
        # for dataset in self.config.dataset_names:
        #     self.target_df[dataset] = self.states["ensemble_entire"].new_gf.df.loc[
        #         self.states["ensemble_entire"].new_gf.df["dataset"] == dataset
        #     ]

    # --------------------------------------------------------------------------
    # TODo: look at the difference in signature
    def _process_states(self):
        states = {}
        # col_names = ["stage", "time"]
        # time_perf_df = pd.DataFrame(columns=col_names)
        for idx, dataset_name in enumerate(self.props["dataset_names"]):
            states[dataset_name] = Dataset(self.props, dataset_name)
            # LOGGER.info("#########################################")
            # LOGGER.info(f"Run: {dataset_name}")
            # LOGGER.info("#########################################")

            # stage1 = time.perf_counter()
            states[dataset_name].create_gf()
            # stage2 = time.perf_counter()
            # LOGGER.info(f"Create GraphFrame: {stage2 - stage1}")
            # LOGGER.info("-----------------------------------------")

            states[dataset_name].process_gf(gf_type="entire")
            # stage3 = time.perf_counter()

            # LOGGER.info(f"Preprocess GraphFrame: {stage3 - stage2}")
            # LOGGER.info("-----------------------------------------")

            states[dataset_name].convert_hatchet_to_nx(gf_type="entire", column_name="path")
            # stage4 = time.perf_counter()
            # LOGGER.info(f"Convert to NetworkX graph: {stage4 - stage3}")
            # LOGGER.info("-----------------------------------------")

            states[dataset_name].group_gf(group_by="module")
            # stage5 = time.perf_counter()
            # LOGGER.info(f"Convert to NetworkX graph: {stage4 - stage3}")
            # LOGGER.info("-----------------------------------------")

            states[dataset_name].write_dataset("entire")
            # stage6 = time.perf_counter()
            # LOGGER.info(f"Write GraphFrame: {stage6 - stage5}")
            # LOGGER.info("-----------------------------------------")

        for idx, dataset_name in enumerate(self.props["dataset_names"]):
            states[dataset_name].read_dataset(gf_type="entire", read_parameters=False)

        stage7 = time.perf_counter()
        states["union_graph"] = Dataset(self.props, 'union_graph')
        states['union_graph'].union(datasets)

        states["union_graph"] = states["union_cct"].union()
        stage8 = time.perf_counter()

        # LOGGER.info(f"Union GraphFrame: {stage8 - stage7}")
        # LOGGER.info("-----------------------------------------")

        states[dataset_name].write_ensemble_gf(states, "ensemble_entire")
        # stage9 = time.perf_counter()
        # LOGGER.info(f"Writing ensemble graph: {stage9 - stage8}")
        # LOGGER.info("-----------------------------------------")

        stage10 = time.perf_counter()
        states["ensemble_filter"] = self.pipeline.filterNetworkX(
            states["ensemble_entire"], self.props["filter_perc"]
        )
        stage11 = time.perf_counter()

        LOGGER.info(f"Filter ensemble graph: {stage11 - stage10}")
        LOGGER.info("-----------------------------------------")

        stage12 = time.perf_counter()
        states[dataset_name].write_ensemble_gf(states, "ensemble_filter")
        stage13 = time.perf_counter()
        LOGGER.info(f"Writing ensemble graph: {stage13 - stage12}")
        LOGGER.info("-----------------------------------------")

        stage14 = time.perf_counter()
        states["ensemble_group"] = self.pipeline.ensemble_group(states, "module")
        stage15 = time.perf_counter()

        LOGGER.info(f"Group ensemble graph: {stage15 - stage14}")
        LOGGER.info("-----------------------------------------")
        stage16 = time.perf_counter()
        states[dataset_name].write_ensemble_gf(states, "ensemble_group")
        stage17 = time.perf_counter()

        LOGGER.info(f"Write group ensemble graph: {stage17 - stage16}")
        LOGGER.info("-----------------------------------------")

        # Need to remove the dependence on reading the dataframe again.
        states = {}
        states["ensemble_entire"].read_ensemble_gf("ensemble_entire")

        stage18 = time.perf_counter()
        aux = EnsembleAuxiliary(
            states,
            MPIBinCount=20,
            RunBinCount=20,
            datasets=self.props["dataset_names"],
            props=self.props,
            process=True,
            write=True,
        )
        aux.run()
        stage19 = time.perf_counter()
        LOGGER.info(f"Dump Gradient, distribution and variations: {stage19 - stage18}")
        LOGGER.info("-----------------------------------------")

        return states

    def _read_states(self):
        states = {}
        states["ensemble_entire"] = self.pipeline.read_ensemble_gf("ensemble_entire")
        states["ensemble_filter"] = self.pipeline.read_ensemble_gf("ensemble_filter")
        states["ensemble_group"] = self.pipeline.read_ensemble_gf("ensemble_group")
        states["all_data"] = self.pipeline.read_all_data()

        return states

    # Write individual functiosn to do this. 
    def _request(self, operation):
        self.add_target_df()
        self.add_basic_info_to_props()
        operation_tag = operation["name"]
        datasets = self.props["dataset_names"]

        if operation_tag == "init":
            return self.props

        elif operation_tag == "ensemble_cct":
            nx = CCT(
                self.datasets, "ensemble_entire", operation["functionsInCCT"]
            )
            LOGGER.debug(nx.g.nodes())
            return nx.g

        elif operation_tag == "supergraph":
            if "reveal_callsites" in operation:
                reveal_callsites = operation["reveal_callsites"]
            else:
                reveal_callsites = []

            if "split_entry_module" in operation:
                split_entry_module = operation["split_entry_module"]
            else:
                split_entry_module = ""

            if "split_callee_module" in operation:
                split_callee_module = action["split_callee_module"]
            else:
                split_callee_module = ""

            self.states["ensemble_group"].g = EnsembleSuperGraph(
                self.states,
                "group_path",
                construct_graph=True,
                add_data=True,
                reveal_callsites=reveal_callsites,
                split_entry_module=split_entry_module,
                split_callee_module=split_callee_module,
            ).agg_g
            return self.states["ensemble_group"].g

        elif operation_tag == "scatterplot":
            if operation["plot"] == "bland-altman":
                state1 = self.states[action["dataset"]]
                state2 = self.states[action["dataset2"]]
                col = operation["col"]
                catcol = operation["catcol"]
                dataset1 = operation["dataset"]
                dataset2 = operation["dataset2"]
                ret = BlandAltman(
                    state1, state2, col, catcol, dataset1, dataset2
                ).results
            return ret

        elif operation_tag == "similarity":
            if operation["module"] == "all":
                dirname = self.config.callflow_dir
                name = self.config.runName
                similarity_filepath = dirname + "/" + "similarity.json"
                with open(similarity_filepath, "r") as similarity_file:
                    self.similarities = json.load(similarity_file)
            else:
                self.similarities = {}
                for idx, dataset in enumerate(datasets):
                    self.similarities[dataset] = []
                    for idx_2, dataset2 in enumerate(datasets):
                        union_similarity = Similarity(
                            self.states[dataset2].g, self.states[dataset].g
                        )
                    self.similarities[dataset].append(union_similarity.result)
            return self.similarities

        elif operation_tag == "hierarchy":
            mH = ModuleHierarchy(
                self.states["ensemble_entire"], operation["module"], config=self.config
            )
            return mH.result

        elif operation_tag == "projection":
            self.similarities = {}
            # dirname = self.config.callflow_dir
            # name = self.config.runName
            # similarity_filepath = dirname  + '/' + 'similarity.json'
            # with open(similarity_filepath, 'r') as similarity_file:
            #     self.similarities = json.load(similarity_file)
            result = ParameterProjection(
                self.states["ensemble_entire"],
                self.similarities,
                operation["targetDataset"],
                n_cluster=operation["numOfClusters"],
            ).result
            return result.to_json(orient="columns")

        elif operation_tag == "run-information":
            ret = []
            for idx, state in enumerate(self.states):
                self.states[state].projection_data["dataset"] = state
                ret.append(self.states[state].projection_data)
            return ret

        elif operation_tag == "mini-histogram":
            minihistogram = MiniHistogram(
                self.states["ensemble"], target_datasets=operation["target-datasets"]
            )
            return minihistogram.result

        elif operation_tag == "histogram":
            histogram = RankHistogram(self.states["ensemble"], operation["module"])
            return histogram.result

        elif operation_tag == "auxiliary":
            print(f"Reprocessing: {operation['re-process']}")
            aux = EnsembleAuxiliary(
                self.states,
                MPIBinCount=operation["MPIBinCount"],
                RunBinCount=operation["RunBinCount"],
                datasets=operation["datasets"],
                config=self.config,
                process=True,
                write=False,
            )
            if action["re-process"] == 1:
                result = aux.run()
            else:
                result = self.states["all_data"]
                # result = aux.filter_dict(result)
            self.currentMPIBinCount = action["MPIBinCount"]
            self.currentRunBinCount = action["RunBinCount"]

            return result

        elif action_name == "compare":
            compareDataset = action["compareDataset"]
            targetDataset = action["targetDataset"]
            if action["selectedMetric"] == "Inclusive":
                selectedMetric = "time (inc)"
            elif action["selectedMetric"] == "Exclusive":
                selectedMetric = "time"

            compare = DiffView(
                self.states["ensemble_entire"],
                compareDataset,
                targetDataset,
                selectedMetric,
            )
            return compare.result

    # --------------------------------------------------------------------------

    def add_basic_info_to_props(self):
        """
        """
        self.props['maxIncTime'] = {}
        self.props['maxExcTime'] = {}
        self.props['minIncTime'] = {}
        self.props['minExcTime'] = {}
        self.props['numOfRanks'] = {}
        maxIncTime = 0
        maxExcTime = 0
        minIncTime = 0
        minExcTime = 0
        maxNumOfRanks = 0
        for idx, dataset in enumerate(self.props["dataset_names"]):
            self.props['maxIncTime'][dataset] = self.target_df[dataset]["time (inc)"].max()
            self.props['maxExcTime'][dataset] = self.target_df[dataset]["time"].max()
            self.props['minIncTime'][dataset] = self.target_df[dataset]["time (inc)"].min()
            self.props['minExcTime'][dataset] = self.target_df[dataset]["time"].min()
            self.props['numOfRanks'][dataset] = len(self.target_df[dataset]["rank"].unique())
            maxExcTime = max(self.props['maxExcTime'][dataset], maxExcTime)
            maxIncTime = max(self.props['maxIncTime'][dataset], maxIncTime)
            minExcTime = min(self.props['minExcTime'][dataset], minExcTime)
            minIncTime = min(self.props['minIncTime'][dataset], minIncTime)
            maxNumOfRanks = max(self.props['numOfRanks'][dataset], maxNumOfRanks)

        self.props['maxIncTime']["ensemble"] = maxIncTime
        self.props['maxExcTime']["ensemble"] = maxExcTime
        self.props['minIncTime']["ensemble"] = minIncTime
        self.props['minExcTime']["ensemble"] = minExcTime
        self.props['numOfRanks']["ensemble"] = maxNumOfRanks

    def add_target_df(self):
        """
        """
        self.target_df = {}
        for dataset in self.props['dataset_names']:
            self.target_df[dataset] = self.datasets["ensemble_entire"].new_gf.df.loc[
                self.datasets["ensemble_entire"].new_gf.df["dataset"] == dataset
            ]