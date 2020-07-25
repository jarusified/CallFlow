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
import os
import json

# ------------------------------------------------------------------------------
# CallFlow imports
import callflow
from callflow import SuperGraph, EnsembleGraph
from callflow.layout import CallFlowNodeLinkLayout, SankeyLayout, HierarchyLayout
from callflow.modules import (
    EnsembleAuxiliary,
    ParameterProjection,
    DiffView,
)
from callflow.operations import Group


LOGGER = callflow.get_logger(__name__)

# ------------------------------------------------------------------------------
# CallFlow class
class CallFlow:
    def __init__(self, config, ensemble=False):
        """
        Entry interface to access CallFlow's functionalities. "
        """

        # Assert if config is provided.
        assert isinstance(config, callflow.operations.ConfigFileReader)

        # Convert config json to props. Never touch self.config ever.
        self.props = json.loads(json.dumps(config, default=lambda o: o.__dict__))

        # True, if ensemble mode is enabled, else False.
        self.ensemble = ensemble

        # Dict of supergraphs.
        self.supergraphs = {}

        # List the datasets that are in CallFlow's vis interface.
        self.datasets_in_vis = self.props["dataset_names"]

    # --------------------------------------------------------------------------
    # Processing methods.
    def _create_dot_callflow_folder(self):
        """
        Create a .callflow directory and empty files.
        """
        LOGGER.debug(f"Saved .callflow directory is: {self.props['save_path']}")

        if not os.path.exists(self.props["save_path"]):
            os.makedirs(self.props["save_path"])
            os.makedirs(os.path.join(self.props["save_path"], "ensemble"))

        dataset_folders = []
        for dataset in self.props["datasets"]:
            dataset_folders.append(dataset["name"])
        dataset_folders.append("ensemble")

        for dataset in dataset_folders:
            dataset_dir = os.path.join(self.props["save_path"], dataset)
            LOGGER.debug(dataset_dir)
            if not os.path.exists(dataset_dir):
                # if self.debug:
                LOGGER.debug(f"Creating .callflow directory for dataset : {dataset}")
                os.makedirs(dataset_dir)

            files = ["df.csv", "nxg.json", "hatchet_tree.txt", "auxiliary_data.json"]
            for f in files:
                fname = os.path.join(dataset_dir, f)
                if not os.path.exists(fname):
                    open(fname, "w").close()

    def _remove_dot_callflow_folder(self):
        """
        TODO: We might want to delete the .callflow folder when we re-process/re-write.
        """
        pass

    def process(self, reprocess_single=True, reprocess_ensemble=True):
        """
        Process the datasets based on the format (i.e., either single or ensemble)
        """
        ndatasets = len(self.datasets_in_vis)
        assert self.ensemble == (ndatasets > 1)

        self._create_dot_callflow_folder()
        if self.ensemble:
            self._process_ensemble(self.datasets_in_vis, reprocess_single, reprocess_ensemble)
        else:
            self._process_single(self.props["dataset_names"][0], reprocess_single)

    def load(self):
        """
        Load the processed datasets by the format.
        """
        ndatasets = len(self.props["dataset_names"])
        if self.ensemble:
            self.supergraphs = self._read_ensemble()
            # assertion here is 1 less than self.supergraph.keys, becasuse
            # self.supergraphs contains the ensemble supergraph as well.
            assert len(self.supergraphs.keys()) == 1 + ndatasets
        else:
            self.supergraphs = self._read_single()
            assert len(self.supergraphs.keys()) == 1

        # Adds basic information to props.
        # Props is later return to client app on "init" request.
        self.add_basic_info_to_props()

    # TODO: Need to incorporate reprocess_single. Address in the next pass. 
    def _process_single(self, dataset, filter=True, reprocess_single=True):
        """
        Single dataset processing.
        """
        supergraph = SuperGraph(props=self.props, tag=dataset, mode="process")
        LOGGER.info("#########################################")
        LOGGER.info(f"Run: {dataset}")
        LOGGER.info("#########################################")

        # Process each graphframe.
        supergraph.process_gf()

        # Filter by inclusive or exclusive time.
        if filter:
            supergraph.filter_gf(mode="single")

        # Group by module.
        # TODO: use self.props.
        Group(supergraph.gf, group_by="module").gf

        # Store the graphframe.
        supergraph.write_gf("entire")

        # Single data auxiliary view processing.
        supergraph.single_auxiliary(
            dataset=dataset, binCount=20, process=True  # _name,
        )

        # We return the single supergraph, so that we can generalize in self._process_single()
        return supergraph

    def _process_ensemble(self, datasets, reprocess_single=True, reprocess_ensemble=True):
        """
        Ensemble processing of datasets.
        """
        # Before we process the ensemble, we perform single processing on all datasets.
        # Process if reprocess_single is true, or if the variable self.supergraphs is empty dict.
        if reprocess_single or len(self.supergraphs.keys()) == 0:
            single_supergraphs = { dataset: self._process_single(dataset, filter=False) for dataset in datasets }
        else:
            single_supergraphs = { dataset: self.supergraphs[dataset] for dataset in datasets }

        if reprocess_ensemble:
            # Create a supergraph class for ensemble case.
            ensemble_supergraph = EnsembleGraph(
                self.props, "ensemble", mode="process", supergraphs=single_supergraphs
            )

            # Filter the ensemble graphframe.
            ensemble_supergraph.filter_gf(mode="ensemble")

            # Group by module.
            ensemble_supergraph.group_gf(group_by="module")

            # Write the grouped graphframe.
            # TODO: remove the parameter, "entire", "group".
            ensemble_supergraph.write_gf("group")

            # Ensemble auxiliary processing.
            ensemble_supergraph.ensemble_auxiliary(
                datasets=datasets,
                MPIBinCount=20,
                RunBinCount=20,
                process=True,
                write=True,
            )

    def _read_single(self):
        """
        Read the single .callflow files required for client.
        """
        supergraphs = {}
        # Only consider the first dataset from the listing.
        dataset_name = self.props["dataset_names"][0]
        supergraphs[dataset_name] = SuperGraph(
            props=self.props, tag=dataset_name, mode="render"
        )

        return supergraphs

    def _read_ensemble(self):
        """
        Read the ensemble .callflow files required for client.
        """
        supergraphs = {}

        for idx, dataset_name in enumerate(self.props["dataset_names"]):
            supergraphs[dataset_name] = SuperGraph(
                self.props, dataset_name, mode="render"
            )
            # supergraphs[dataset_name].read_gf(read_parameter=self.props["read_parameter"])

        supergraphs["ensemble"] = EnsembleGraph(
            props=self.props, tag="ensemble", mode="render"
        )
        # supergraphs["ensemble"].read_gf(read_parameter=self.props["read_parameter"])
        # supergraphs["ensemble"].read_auxiliary_data()
        return supergraphs

    # --------------------------------------------------------------------------
    # Reading and rendering methods.
    # All the functions below are Public methods that are accessed by the server.

    def add_basic_info_to_props(self):
        """
        Adds basic information (like max, min inclusive and exclusive runtime) to self.props.
        """
        self.props["maxIncTime"] = {}
        self.props["maxExcTime"] = {}
        self.props["minIncTime"] = {}
        self.props["minExcTime"] = {}
        self.props["numOfRanks"] = {}
        maxIncTime = 0
        maxExcTime = 0
        minIncTime = 0
        minExcTime = 0
        maxNumOfRanks = 0
        for idx, tag in enumerate(self.supergraphs):
            self.props["maxIncTime"][tag] = (
                self.supergraphs[tag].gf.df["time (inc)"].max()
            )
            self.props["maxExcTime"][tag] = self.supergraphs[tag].gf.df["time"].max()
            self.props["minIncTime"][tag] = (
                self.supergraphs[tag].gf.df["time (inc)"].min()
            )
            self.props["minExcTime"][tag] = self.supergraphs[tag].gf.df["time"].min()
            # self.props["numOfRanks"][dataset] = len(
            #     self.datasets[dataset].gf.df["rank"].unique()
            # )
            maxExcTime = max(self.props["maxExcTime"][tag], maxExcTime)
            maxIncTime = max(self.props["maxIncTime"][tag], maxIncTime)
            minExcTime = min(self.props["minExcTime"][tag], minExcTime)
            minIncTime = min(self.props["minIncTime"][tag], minIncTime)
            # maxNumOfRanks = max(self.props["numOfRanks"][dataset], maxNumOfRanks)

        self.props["maxIncTime"]["ensemble"] = maxIncTime
        self.props["maxExcTime"]["ensemble"] = maxExcTime
        self.props["minIncTime"]["ensemble"] = minIncTime
        self.props["minExcTime"]["ensemble"] = minExcTime
        # self.props["numOfRanks"]["ensemble"] = maxNumOfRanks

    def request_single(self, operation):
        """
        Handles all the socket requests connected to Single CallFlow.
        """
        _OPERATIONS = [
            "init",
            "reset",
            "auxiliary",
            "cct",
            "supergraph",
            "miniHistogram",
            "function",
        ]
        assert "name" in operation
        assert operation["name"] in _OPERATIONS

        LOGGER.info(f"[Single Mode] {operation}")
        operation_name = operation["name"]

        if operation_name == "init":
            return self.props

        elif operation_name == "auxiliary":
            return self.supergraphs[operation["dataset"]].auxiliary_data

        elif operation_name == "cct":
            result = CallFlowNodeLinkLayout(
                graphframe=self.supergraphs[operation["dataset"]].gf,
                filter_metric=operation["filter_metric"],
                filter_count=operation["filter_count"],
            )
            return result.nxg

        elif operation_name == "supergraph":
            single_supergraph = SankeyLayout(
                supergraph=self.supergraphs[operation["dataset"]], path="group_path"
            )
            return single_supergraph.nxg

        elif operation_name == "miniHistogram":
            minihistogram = MiniHistogram(state)
            return minihistogram.result

        elif operation_name == "function":
            functionlist = FunctionList(state, operation["module"])
            return functionlist.result

    def request_ensemble(self, operation):
        """
        Handles all the socket requests connected to Single CallFlow.
        """

        _OPERATIONS = [
            "init",
            "reset",
            "auxiliary",
            "cct",
            "supergraph",
            "projection",
            "hierarchy",
            "run-information",
            "similarity",
            "compare"
        ]
        assert "name" in operation
        assert operation["name"] in _OPERATIONS

        LOGGER.info(f"[Ensemble Mode] {operation}")
        operation_name = operation["name"]

        # Determine if we need to re-process or not.
        # Reprocessing happens when the user requests a different set of graphs
        # from `self.datasets_in_vis`
        if "datasets" in operation and set(operation["datasets"]) != set(self.datasets_in_vis):
            self.datasets_in_vis = operation["datasets"]
            self.process(reprocess_single=False, reprocess_ensemble=True)

        if operation_name == "init":
            return self.props

        elif operation_name == "cct":
            result = NodeLinkLayout(
                graphframe=self.supergraphs["ensemble"].gf,
                filter_metric=operation["filter_metric"],
                filter_count=operation["functionsInCCT"],
            )
            return result.nxg

        elif operation_name == "supergraph":
            if "reveal_callsites" in operation:
                reveal_callsites = operation["reveal_callsites"]
            else:
                reveal_callsites = []

            if "split_entry_module" in operation:
                split_entry_module = operation["split_entry_module"]
            else:
                split_entry_module = ""

            if "split_callee_module" in operation:
                split_callee_module = operation["split_callee_module"]
            else:
                split_callee_module = ""

            ensemble_super_graph = SankeyLayout(
                supergraph=self.supergraphs["ensemble"], path="group_path"
            )
            return ensemble_super_graph.nxg

        elif operation_name == "hierarchy":
            modulehierarchy = HierarchyLayout(
                self.supergraphs["ensemble"], operation["module"]
            )
            return modulehierarchy.nxg

        elif operation_name == "projection":
            projection = ParameterProjection(
                supergraph=self.supergraphs["ensemble"],
                targetDataset=operation["targetDataset"],
                n_cluster=operation["numOfClusters"],
            )
            return projection.result.to_json(orient="columns")

        # Not used.
        elif operation_name == "scatterplot":
            assert False
            if operation["plot"] == "bland-altman":
                state1 = self.states[operation["dataset"]]
                state2 = self.states[operation["dataset2"]]
                col = operation["col"]
                catcol = operation["catcol"]
                dataset1 = operation["dataset"]
                dataset2 = operation["dataset2"]
                ret = BlandAltman(
                    state1, state2, col, catcol, dataset1, dataset2
                ).results
            return ret

        # Not used.
        elif operation_name == "similarity":
            assert False
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

        # Not used.
        elif operation_name == "run-information":
            assert False
            ret = []
            for idx, state in enumerate(self.states):
                self.states[state].projection_data["dataset"] = state
                ret.append(self.states[state].projection_data)
            return ret

        elif operation_name == "auxiliary":
            if len(operation["datasets"]) > 1:
                return self.supergraphs["ensemble"].auxiliary_data
            return self.supergraphs[operation["datasets"][0]].auxiliary_data

        elif operation_name == "compare":
            compareDataset = operation["compareDataset"]
            targetDataset = operation["targetDataset"]
            if operation["selectedMetric"] == "Inclusive":
                selectedMetric = "time (inc)"
            elif operation["selectedMetric"] == "Exclusive":
                selectedMetric = "time"

            compare = DiffView(
                self.supergraphs["ensemble"],
                compareDataset,
                targetDataset,
                selectedMetric,
            )
            return compare.result
