/** 
 * Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
 * CallFlow Project Developers. See the top-level LICENSE file for details.
 * 
 * SPDX-License-Identifier: MIT
 */

import * as d3 from "d3";

import Color from "../lib/color/color";
import Splitpanes from "splitpanes";
import "splitpanes/dist/splitpanes.css";

import EventHandler from "./EventHandler";

// Template import
import tpl from "../html/callflowSingle.html";

import SuperGraph from "./supergraph/supergraph";
import CCT from "./cct/cct";

// Single mode imports
import SingleScatterplot from "./singleScatterplot/singleScatterplot";
import SingleHistogram from "./singleHistogram/singleHistogram";
import CallsiteInformation from "./callsiteInformation/callsiteInformation";

// Ensemble mode imports
import CallsiteCorrespondence from "./callsiteCorrespondence/callsiteCorrespondence";
import EnsembleHistogram from "./ensembleHistogram/ensembleHistogram";
import ModuleHierarchy from "./moduleHierarchy/moduleHierarchy";
import EnsembleScatterplot from "./ensembleScatterplot/ensembleScatterplot";
import ParameterProjection from "./parameterProjection/parameterProjection";

import io from "socket.io-client";
import * as utils from "./utils";

export default {
	name: "SingleCallFlow",
	template: tpl,
	components: {
		Splitpanes,
		// Generic components
		SuperGraph,
		CCT,
		// Single supergraph components.
		SingleScatterplot,
		SingleHistogram,
		CallsiteInformation,
		// Ensemble supergraph components.
		EnsembleScatterplot,
		EnsembleHistogram,
		ModuleHierarchy,
		ParameterProjection,
		CallsiteCorrespondence,
	},

	watch: {
		showTarget: (val) => {
			EventHandler.$emit("show_target_auxiliary");
		}
	},

	data: () => ({
		appName: "CallFlow",
		server: "localhost:5000",
		config: {
			headers: {
				"Access-Control-Allow-Origin": "*"
			}
		},
		left: false,
		formats: ["CCT", "SuperGraph"],
		selectedFormat: "SuperGraph",
		datasets: [],
		selectedTargetDataset: "",
		selectedDataset2: "",
		groupBy: ["Name", "Module", "File"],
		selectedGroupBy: "Module",
		filterBy: ["Inclusive", "Exclusive"],
		filterRange: [0, 100],
		selectedFilterBy: "Inclusive",
		selectedIncTime: 0,
		filterPercRange: [0, 100],
		selectedFilterPerc: 5,
		metrics: ["Exclusive", "Inclusive"],//, 'Imbalance'],
		selectedMetric: "Exclusive",
		runtimeColorMap: [],
		distributionColorMap: [],
		selectedRuntimeColorMap: "OrRd",
		colorPoints: [3, 4, 5, 6, 7, 8, 9],
		selectedColorPoint: 9,
		selectedColorMin: null,
		selectedColorMax: null,
		selectedColorMinText: "",
		selectedColorMaxText: "",
		groupModes: ["include callbacks", "exclude callbacks"],
		selectedGroupMode: "include callbacks",
		scatterMode: ["mean", "all"],
		selectedScatterMode: "all",
		selectedFunctionsInCCT: 70,
		isCallgraphInitialized: false,
		isCCTInitialized: false,
		datas: ["Dataframe", "Graph"],
		selectedData: "Dataframe",
		firstRender: true,
		summaryChip: "SuperGraph",
		auxiliarySortBy: "time (inc)",
		ranks: [],
		initLoad: true,
		comparisonMode: false,
		selectedCompareDataset: null,
		selectedOutlierBand: 4,
		defaultCallSite: "<program root>",
		modes: ["Ensemble", "Single"],
		selectedMode: "Single",
		// Presentation mode variables
		exhibitModes: ["Presentation", "Default"],
		selectedExhibitMode: "Default",
		selectedMPIBinCount: 20,
		selectedRuntimeSortBy: "Inclusive",
		sortByModes: ["Inclusive", "Exclusive", "Standard Deviation"],
		scales: ["Log", "Linear"],
		selectedScale: "Linear",
		props: ["name", "rank", "dataset", "all_ranks"],
		selectedProp: "rank",
		metricTimeMap: {}, // Stores the metric map for each dataset (sorted by inclusive/exclusive time),
		selectedRunBinCount: 20,
	}),

	mounted() {
		var socket = io.connect(this.server, { reconnect: false });
		this.$socket.emit("init", {
			mode: this.selectedMode,
		});

		EventHandler.$on("lasso_selection", () => {
			this.$store.resetTargetDataset = true;

			this.clearLocal();
			this.setTargetDataset();
			this.$socket.emit("ensemble_callsite_data", {
				datasets: this.$store.selectedDatasets,
				sortBy: this.$store.auxiliarySortBy,
				MPIBinCount: this.$store.selectedMPIBinCount,
				RunBinCount: this.$store.selectedRunBinCount,
				module: "all",
				"re_process": 1
			});
		});

		EventHandler.$on("show_target_auxiliary", () => {
			this.clearLocal();
			this.init();
		});
	},

	beforeDestroy() {
		//Unsubscribe on destroy
		this.$socket.emit("disconnect");
	},

	sockets: {
		// Assign variables for the store and Callflow ui component.
		// Assign colors and min, max inclusive and exclusive times.
		init(data) {
			this.setupStore(data);
			this.setTargetDataset();
			this.setComponentMap();
			if (this.selectedFormat == "SuperGraph") {
				this.$socket.emit("ensemble_callsite_data", {
					datasets: this.$store.selectedDatasets,
					sortBy: this.$store.auxiliarySortBy,
					MPIBinCount: this.$store.selectedMPIBinCount,
					RunBinCount: this.$store.selectedRunBinCount,
					module: "all",
					re_process: this.$store.reprocess
				});
			}
			else if (this.selectedFormat == "CCT") {
				this.init();
			}
		},

		ensemble_callsite_data(data) {
			console.log("Auxiliary Data: ", data);
			this.dataReady = true;

			this.$store.modules = data["module"];
			this.$store.callsites = data["callsite"];
			this.$store.gradients = data["gradients"];
			this.$store.moduleCallsiteMap = data["moduleCallsiteMap"];
			this.$store.callsiteModuleMap = data["callsiteModuleMap"];
			this.init();
		},

		// Reset to the init() function.
		reset(data) {
			console.log("Data for", this.selectedFormat, ": ", data);
			this.init();
		},

		disconnect() {
			console.log("Disconnected.");
		}
	},

	methods: {
		// Feature: Sortby the datasets and show the time.
		formatRuntimeWithoutUnits(val) {
			let format = d3.format(".2");
			let ret = format(val);
			return ret;
		},

		// Feature: Sortby the datasets and show the time.
		sortDatasetsByAttr(datasets, attr) {
			if (datasets.length == 1) {
				this.metricTimeMap[datasets[0]] = this.$store.maxIncTime[datasets[0]];
				return datasets;
			}
			let ret = datasets.sort((a, b) => {
				let x = 0, y = 0;
				if (attr == "Inclusive") {
					x = this.$store.maxIncTime[a];
					y = this.$store.maxIncTime[b];
					this.metricTimeMap = this.$store.maxIncTime;
				}
				else if (attr == "Exclusive") {
					x = this.$store.maxExcTime[a];
					y = this.$store.maxExcTime[b];
					this.metricTimeMap = this.$store.maxExcTime;
				}
				return parseFloat(x) - parseFloat(y);
			});
			return ret;
		},

		setViewDimensions() {
			this.$store.viewWidth = window.innerWidth;

			let toolbarHeight = 0;
			let footerHeight = 0;
			// Set toolbar height as 0 if undefined
			if (document.getElementById("toolbar") == null) {
				toolbarHeight = 0;
			}
			else {
				toolbarHeight = document.getElementById("toolbar").clientHeight;
			}
			if (document.getElementById("footer") == null) {
				footerHeight = 0;
			}
			else {
				footerHeight = document.getElementById("footer").clientHeight;
			}
			this.$store.viewHeight = window.innerHeight - toolbarHeight - footerHeight;
		},

		setupStore(data) {
			data = JSON.parse(data);
			console.log("Config file: ", data);
			this.$store.numOfRuns = data["datasets"].length;
			this.$store.selectedDatasets = data["names"];
			this.datasets = this.$store.selectedDatasets;

			// Enable diff mode only if the number of datasets >= 2
			if (this.numOfRuns >= 2) {
				this.modes = ["Single", "Ensemble"];
				this.selectedMode = "Ensemble";
			}
			else if (this.numOfRuns == 1) {
				this.enableDist = false;
				this.modes = ["Single"];
				this.selectedMode = "Single";
			}

			this.$store.maxExcTime = data["maxExcTime"];
			this.$store.minExcTime = data["minExcTime"];
			this.$store.maxIncTime = data["maxIncTime"];
			this.$store.minIncTime = data["minIncTime"];

			this.$store.numOfRanks = data["numOfRanks"];
			this.$store.moduleCallsiteMap = data["module_callsite_map"];
			this.$store.callsiteModuleMap = data["callsite_module_map"];

			this.$store.selectedMPIBinCount = this.selectedMPIBinCount;
			this.$store.selectedRunBinCount = this.selectedRunBinCount;

			this.setViewDimensions();

			this.$store.auxiliarySortBy = this.auxiliarySortBy;
			this.$store.reprocess = 0;
			this.$store.comparisonMode = this.comparisonMode;
			this.$store.fontSize = 14;
			this.$store.transitionDuration = 1000;
			this.$store.encoding = "MEAN";
		},

		setOtherData() {
			this.$store.selectedScatterMode = "mean";
			this.$store.nodeInfo = {};
			this.$store.selectedMode = this.selectedMode;
			this.$store.selectedFunctionsInCCT = this.selectedFunctionsInCCT;
			this.$store.selectedHierarchyMode = this.selectedHierarchyMode;
			if (this.$store.selectedMode == "Single") {
				this.$store.selectedProp = "rank";
			}

			this.$store.selectedScale = this.selectedScale;
			this.$store.selectedCompareMode = this.selectedCompareMode;
			this.$store.selectedIQRFactor = this.selectedIQRFactor;
			this.$store.selectedRuntimeSortBy = this.selectedRuntimeSortBy;
			this.$store.selectedNumOfClusters = this.selectedNumOfClusters;
			this.$store.selectedEdgeAlignment = "Top";

			this.$store.datasetMap = {};
			for (let i = 0; i < this.$store.selectedDatasets.length; i += 1) {
				this.$store.datasetMap[this.$store.selectedDatasets[i]] = "run-" + i;
			}

			this.$store.contextMenu = this.contextMenu;
			this.$store.selectedSuperNodePositionMode = "Minimal edge crossing";
		},

		setTargetDataset() {
			if (this.firstRender) {
				this.$store.resetTargetDataset = true;
			}
			this.$store.selectedMetric = this.selectedMetric;
			this.datasets = this.sortDatasetsByAttr(this.$store.selectedDatasets, "Inclusive");

			let max_dataset = "";
			let current_max_time = 0.0;

			let data = {};
			if (this.$store.selectedMetric == "Inclusive") {
				data = this.$store.maxIncTime;
			}
			else if (this.$store.selectedMetric == "Exclusive") {
				data = this.$store.maxExcTime;
			}

			for (let dataset of this.$store.selectedDatasets) {
				if (current_max_time < data[dataset]) {
					current_max_time = data[dataset];
					max_dataset = dataset;
				}
			}
			if (this.firstRender || this.$store.resetTargetDataset) {
				this.$store.selectedTargetDataset = max_dataset;
				this.selectedTargetDataset = max_dataset;
				this.firstRender = false;
				this.$store.resetTargetDataset = false;
			}
			else {
				this.$store.selectedTargetDataset = this.selectedTargetDataset;
			}
			this.selectedIncTime = ((this.selectedFilterPerc * this.$store.maxIncTime[this.selectedTargetDataset] * 0.000001) / 100).toFixed(3);

			console.log("Maximum among all runtimes: ", this.selectedTargetDataset);
		},

		setComponentMap() {
			this.currentSingleCCTComponents = [this.$refs.SingleCCT];
			this.currentSingleSuperGraphComponents = [
				this.$refs.SingleSuperGraph,
				this.$refs.SingleHistogram,
				this.$refs.SingleScatterplot,
				this.$refs.CallsiteInformation,
			];
		},

		// Set the min and max and assign color variables from Settings.
		setRuntimeColorScale() {
			let colorMin = null;
			let colorMax = null;
			if (this.selectedMode == "Ensemble") {
				if (this.selectedMetric == "Inclusive") {
					colorMin = parseFloat(this.$store.minIncTime["ensemble"]);
					colorMax = parseFloat(this.$store.maxIncTime["ensemble"]);
				}
				else if (this.selectedMetric == "Exclusive") {
					colorMin = parseFloat(this.$store.minExcTime["ensemble"]);
					colorMax = parseFloat(this.$store.maxExcTime["ensemble"]);
				}
				else if (this.selectedMetric == "Imbalance") {
					colorMin = 0.0;
					colorMax = 1.0;
				}
			}
			else if (this.selectedMode == "Single") {
				if (this.selectedMetric == "Inclusive") {
					colorMin = parseFloat(this.$store.minIncTime[this.selectedTargetDataset]);
					colorMax = parseFloat(this.$store.maxIncTime[this.selectedTargetDataset]);
				}
				else if (this.selectedMetric == "Exclusive") {
					colorMin = parseFloat(this.$store.minExcTime[this.selectedTargetDataset]);
					colorMax = parseFloat(this.$store.maxExcTime[this.selectedTargetDataset]);
				}
				else if (this.selectedMetric == "Imbalance") {
					colorMin = 0.0;
					colorMax = 1.0;
				}
			}

			this.selectedColorMinText = utils.formatRuntimeWithoutUnits(parseFloat(colorMin));
			this.selectedColorMaxText = utils.formatRuntimeWithoutUnits(parseFloat(colorMax));

			this.$store.selectedColorMin = this.colorMin;
			this.$store.selectedColorMax = this.colorMax;

			this.$store.runtimeColor.setColorScale(this.$store.selectedMetric, colorMin, colorMax, this.selectedRuntimeColorMap, this.selectedColorPoint);
		},

		setupColors() {
			// Create color object.
			this.$store.runtimeColor = new Color();
			this.runtimeColorMap = this.$store.runtimeColor.getAllColors();
			this.setRuntimeColorScale();

			// Set properties into store.
			this.$store.selectedRuntimeColorMap = this.selectedRuntimeColorMap;
			this.$store.selectedDistributionColorMap = this.selectedDistributionColorMap;
			this.$store.selectedColorPoint = this.selectedColorPoint;

			this.$store.runtimeColor.intermediate = "#d9d9d9";
			this.$store.runtimeColor.highlight = "#C0C0C0";
			this.$store.runtimeColor.textColor = "#3a3a3a";
			this.$store.runtimeColor.edgeStrokeColor = "#888888";
		},

		// Feature: the Supernode hierarchy is automatically selected from the mean metric runtime.
		sortModulesByMetric(attr) {
			let module_list = Object.keys(this.$store.modules[this.selectedTargetDataset]);

			// Create a map for each dataset mapping the respective mean times.
			let map = {};
			for (let module_name of module_list) {
				map[module_name] = this.$store.modules[this.selectedTargetDataset][module_name][this.$store.selectedMetric]["mean_time"];
			}

			// Create items array
			let items = Object.keys(map).map(function (key) {
				return [key, map[key]];
			});

			// Sort the array based on the second element
			items.sort(function (first, second) {
				return second[1] - first[1];
			});

			return items;
		},

		setSelectedModule() {
			let modules_sorted_list_by_metric = this.sortModulesByMetric();
			this.selectedModule = modules_sorted_list_by_metric[0][0];
			this.$store.selectedModule = this.selectedModule;
		},

		clear() {
			if (this.selectedFormat == "CCT") {
				this.clearComponents(this.currentSingleCCTComponents);
			}
			else if (this.selectedFormat == "SuperGraph") {
				this.clearComponents(this.currentSingleSuperGraphComponents);
			}
		},

		clearLocal() {
			if (this.selectedFormat == "CCT") {
				this.clearComponents(this.currentSingleSuperGraphComponents);
			}
			else if (this.selectedFormat == "SuperGraph") {
				this.clearComponents(this.currentSingleCCTComponents);
			}

		},

		initComponents(componentList) {
			for (let i = 0; i < componentList.length; i++) {
				componentList[i].init();
			}
		},

		clearComponents(componentList) {
			for (let i = 0; i < componentList.length; i++) {
				componentList[i].clear();
			}
		},

		init() {
			// Initialize colors
			this.setupColors();
			this.setOtherData();
			if (this.selectedFormat == "SuperGraph") {
				this.setSelectedModule();
			}

			console.log("Mode : ", this.selectedMode);
			console.log("Number of runs :", this.$store.numOfRuns);
			console.log("Dataset : ", this.selectedTargetDataset);
			console.log("Format = ", this.selectedFormat);

			// Call the appropriate socket to query the server.
			if (this.selectedMode == "Single") {

				if (this.selectedFormat == "SuperGraph") {
					this.initComponents(this.currentSingleSuperGraphComponents);
				}
				else if (this.selectedFormat == "CCT") {
					this.initComponents(this.currentSingleCCTComponents);
				}
			}
			else if (this.selectedMode == "Ensemble") {
				if (this.selectedFormat == "SuperGraph") {
					this.initComponents(this.currentEnsembleSuperGraphComponents);
				}
				else if (this.selectedFormat == "CCT") {
					this.initComponents(this.currentEnsembleCCTComponents);
				}
			}
		},

		reset() {
			this.$socket.emit("init", {
				mode: this.selectedMode,
				dataset: this.$store.selectedTargetDataset
			});
		},

		updateColors() {
			this.clearLocal();
			this.setupColors();
			this.init();
		},

		updateFormat() {
			this.clearLocal();
			this.$socket.emit("init", {
				mode: this.selectedMode,
				dataset: this.$store.selectedTargetDataset
			});
			this.init();
		},

		updateTargetDataset() {
			this.clear();
			this.$store.selectedTargetDataset = this.selectedTargetDataset;
			console.debug("[Update] Target Dataset: ", this.selectedTargetDataset);
			this.init();
			EventHandler.$emit("show_target_auxiliary", {
			});
		},

		updateMode() {
			this.clear();
			this.init();
		},

		updateMetric() {
			this.$store.selectedMetric = this.selectedMetric;
			this.clearLocal();
			this.init();
		},

		updateColor() {
			this.clearLocal();
			this.init();
		},

		updateColorPoint() {
			this.clearLocal();
			this.init();
		},

		updateFunctionsInCCT() {
			this.$socket.emit("cct", {
				dataset: this.$store.selectedTargetDataset,
				functionInCCT: this.selectedFunctionsInCCT,
			});
		},

		updateScale() {
			this.$store.selectedScale = this.selectedScale;
			this.clear();
			this.init();
		},

		updateIQRFactor() {
			this.$store.selectedIQRFactor = this.selectedIQRFactor;
			this.clearLocal();
			this.init();
		},

		updateRuntimeSortBy() {
			this.$store.selectedRuntimeSortBy = this.selectedRuntimeSortBy;
			EventHandler.$emit("callsite_information_sort");
		},

		updateMPIBinCount() {
			this.$store.selectedMPIBinCount = this.selectedMPIBinCount;
			this.$store.reprocess = 1;
			this.$socket.emit("ensemble_callsite_data", {
				datasets: this.$store.selectedDatasets,
				sortBy: this.$store.auxiliarySortBy,
				MPIBinCount: this.$store.selectedMPIBinCount,
				RunBinCount: this.$store.selectedRunBinCount,
				module: "all",
				re_process: 1
			});
			this.clearLocal();
			this.init();
		}
	}
};