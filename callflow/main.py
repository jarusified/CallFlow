import os
import json

import callflow
from callflow import SuperGraph, EnsembleGraph
LOGGER = callflow.get_logger(__name__)

class CallFlow:
    def __init__(self, config={}, process=False, ensemble=False):

        # Assert if config is provided.
        assert config != None

        # Convert config json to props. Never touch self.config ever.
        self.props = json.loads(json.dumps(config, default=lambda o: o.__dict__))
       
        # Based on option, either process into .callflow or read from .callflow.
        if process:
            self._create_dot_callflow_folder()
            if ensemble:
                self._process_datasets_ensemble()
            else:
                self._process_datasets_single()
        else:
            if ensemble:
                self.datasets = self._read_datasets_ensemble()

            self.add_target_df()
            self.add_basic_info_to_props()


    # --------------------------------------------------------------------------
    def _process_datasets_single(self):
        """
        Single dataset processing. 
        """
        dataset_name = self.props["dataset_names"][0]
        dataset = Dataset(self.props, dataset_name)
        LOGGER.info("#########################################")
        LOGGER.info(f"Run: {dataset_name}")
        LOGGER.info("#########################################")

        # Process each graphframe.
        dataset.process_gf()

        # Filter by inclusive or exclusive time.
        dataset.filter_gf(mode="single")

        # Group by module.
        dataset.group_gf(group_by="module")

        # Store the graphframe.
        dataset.write_gf("entire")

    def _process_datasets_ensemble(self):
        """
        Ensemble processing of datasets. 
        """
        # Single dataset processing.
        single_datasets = {}
        for idx, dataset_name in enumerate(self.props["dataset_names"]):
            # Create an instance of dataset.
            single_datasets[dataset_name] = SuperGraph(self.props, dataset_name, mode="process", datasets={})
            LOGGER.info("#########################################")
            LOGGER.info(f"Run: {dataset_name}")
            LOGGER.info("#########################################")

            # Process each graphframe.
            single_datasets[dataset_name].process_gf()

            # Write the entire graphframe into .callflow.
            single_datasets[dataset_name].write_gf("entire")

        # Create a dataset for ensemble case.
        ensemble_dataset = EnsembleGraph(self.props, "ensemble", mode="process", datasets=single_datasets)
        # Write the graphframe to file. 
        ensemble_dataset.write_gf("entire")

        # Filter the ensemble graphframe.
        ensemble_dataset.filter_gf(mode="ensemble")

        # Write the filtered graphframe.
        ensemble_dataset.write_gf("filter")

        # Group by module.
        ensemble_dataset.group_gf(group_by="module")

        # Write the grouped graphframe.
        ensemble_dataset.write_gf("group")

        # Calculate auxiliary information (used by callflow app.)
        ensemble_dataset.auxiliary(
            # MPIBinCount=self.currentMPIBinCount,
            # RunBinCount=self.currentRunBinCount,
            MPIBinCount=20,
            RunBinCount=20,
            process=True,
            write=True,
        )

    # --------------------------------------------------------------------------
    def _read_datasets_single(self):
        """
        Read the single .callflow files required for client.
        """
        dataset_name = self.props["dataset_names"][0]
        dataset = Dataset(self.props, dataset_name)
        dataset.read_gf(gf_type="entire", read_parameter=self.props["read_parameter"])
        return dataset

    def _read_datasets_ensemble(self):
        """
        Read the ensemble .callflow files required for client.
        """
        datasets = {}

        for idx, dataset_name in enumerate(self.props["dataset_names"]):
            datasets[dataset_name] = SuperGraph(self.props, dataset_name, mode="render")
            datasets[dataset_name].read_gf(gf_type="entire", read_parameter=self.props["read_parameter"])

        datasets["ensemble"] = Dataset(self.props, "ensemble")
        datasets["ensemble"].read_gf("entire", read_parameter=self.props["read_parameter"])
        datasets["ensemble"].read_gf("filter", read_parameter=self.props["read_parameter"])
        datasets["ensemble"].read_gf("group", read_parameter=self.props["read_parameter"])
        datasets["ensemble"].read_auxiliary_data()
        return datasets
    # --------------------------------------------------------------------------
    def add_target_df(self):
        """
        """
        self.target_df = {}
        for dataset in self.props["dataset_names"]:
            self.target_df[dataset] = self.datasets["ensemble"].gf.df.loc[
                self.datasets["ensemble"].gf.df["dataset"] == dataset
            ]

    def add_basic_info_to_props(self):
        """
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
        for idx, dataset in enumerate(self.props["dataset_names"]):
            self.props["maxIncTime"][dataset] = self.target_df[dataset][
                "time (inc)"
            ].max()
            self.props["maxExcTime"][dataset] = self.target_df[dataset]["time"].max()
            self.props["minIncTime"][dataset] = self.target_df[dataset][
                "time (inc)"
            ].min()
            self.props["minExcTime"][dataset] = self.target_df[dataset]["time"].min()
            self.props["numOfRanks"][dataset] = len(
                self.target_df[dataset]["rank"].unique()
            )
            maxExcTime = max(self.props["maxExcTime"][dataset], maxExcTime)
            maxIncTime = max(self.props["maxIncTime"][dataset], maxIncTime)
            minExcTime = min(self.props["minExcTime"][dataset], minExcTime)
            minIncTime = min(self.props["minIncTime"][dataset], minIncTime)
            maxNumOfRanks = max(self.props["numOfRanks"][dataset], maxNumOfRanks)

        self.props["maxIncTime"]["ensemble"] = maxIncTime
        self.props["maxExcTime"]["ensemble"] = maxExcTime
        self.props["minIncTime"]["ensemble"] = minIncTime
        self.props["minExcTime"]["ensemble"] = minExcTime
        self.props["numOfRanks"]["ensemble"] = maxNumOfRanks

    # --------------------------------------------------------------------------
    def _create_dot_callflow_folder(self):
        """
        Create a .callflow directory and empty files.
        """
        LOGGER.debug(f"Saved .callflow directory is: {self.props['save_path']}")

        if not os.path.exists(self.props["save_path"]):
            os.makedirs(self.props["save_path"])
            os.makedirs(os.path.join(self.props["save_path"], "ensemble"))

        for dataset in self.props["datasets"]:
            dataset_dir = os.path.join(self.props["save_path"], dataset["name"])
            LOGGER.debug(dataset_dir)
            if not os.path.exists(dataset_dir):
                # if self.debug:
                LOGGER.debug(
                    f"Creating .callflow directory for dataset : {dataset['name']}"
                )
                os.makedirs(dataset_dir)

            files = [
                "entire_df.csv",
                "filter_df.csv",
                "entire_nxg.json",
                "filter_nxg.json",
            ]
            for f in files:
                fname = os.path.join(dataset_dir, f)
                if not os.path.exists(fname):
                    open(fname, "w").close()

    # --------------------------------------------------------------------------
    def request_single(self, operation):
        LOGGER.info(f"[Single Mode] {operation}")
        operation_tag = operation["name"]

        if operation_tag == "init":
            return self.props

        if "groupBy" in operation:
            LOGGER.info("Grouping by: {0}".format(operation["groupBy"]))
        else:
            operation["groupBy"] = "name"

        dataset = operation["dataset"]
        state = self.states[dataset]

        LOGGER.info("The selected Dataset is {0}".format(dataset))

        # Compare against the different operations
        if operation_tag == "reset":
            datasets = [dataset]
            self.reProcess = True
            self.states = self.pipeline(
                datasets, operation["filterBy"], operation["filterPerc"]
            )
            self.reProcess = False
            self.states = self.pipeline(datasets)
            return {}

        elif operation_tag == "auxiliary":
            auxiliary = Auxiliary(
                self.states[operation["dataset"]],
                binCount=operation["binCount"],
                dataset=operation["dataset"],
                config=self.config,
            )
            return auxiliary.result

        elif operation_tag == "supergraph":
            self.states[dataset].g = SuperGraph(
                self.states, dataset, "group_path", construct_graph=True, add_data=True
            ).g
            return self.states[dataset].g

        elif operation_tag == "mini-histogram":
            minihistogram = MiniHistogram(state)
            return minihistogram.result

        elif operation_tag == "cct":
            graph = CCT(
                self.states[operation["dataset"]], operation["functionsInCCT"], self.config
            )
            return graph.g

        elif operation_tag == "function":
            functionlist = FunctionList(state, operation["module"], operation["nid"])
            return functionlist.result

    # Write individual functiosn to do this.
    def request_ensemble(self, operation):
        operation_tag = operation["name"]
        datasets = self.props["dataset_names"]

        if operation_tag == "init":
            return self.props

        elif operation_tag == "ensemble_cct":
            nx = CCT(self.datasets, "ensemble_entire", operation["functionsInCCT"])
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
                split_callee_module = operation["split_callee_module"]
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
            if operation["re-process"] == 1:
                result = aux.run()
            else:
                result = self.states["all_data"]
                result = aux.filter_dict(result)
            self.currentMPIBinCount = operation["MPIBinCount"]
            self.currentRunBinCount = operation["RunBinCount"]

            return result

        elif operation_tag == "compare":
            compareDataset = operation["compareDataset"]
            targetDataset = operation["targetDataset"]
            if operation["selectedMetric"] == "Inclusive":
                selectedMetric = "time (inc)"
            elif operation["selectedMetric"] == "Exclusive":
                selectedMetric = "time"

            compare = DiffView(
                self.states["ensemble_entire"],
                compareDataset,
                targetDataset,
                selectedMetric,
            )
            return compare.result
