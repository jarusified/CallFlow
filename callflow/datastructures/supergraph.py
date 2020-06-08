import os
import json
import copy
import networkx as nx
import callflow
from networkx.readwrite import json_graph

from callflow.operations import Process, Group, Filter
from callflow.modules import EnsembleAuxiliary


class SuperGraph(object):
    def __init__(self, props={}, tag="", mode="process", datasets={}):

        self.datasets = datasets
        # Props is the information contained in config object. 
        # We duplicate this to add more information to config and not modify it as a side effect. 
        self.props = props
        self.dirname = self.props["save_path"]

        # it appears we're using name as "union", "filter", etc. 
        # this is not a data set name!
        self.tag = tag

        # Mode is either process or render. 
        self.mode = mode

        # instead of the old variables, we will use these new ones.
        # these are callflow.graphframe object (has gf, df, and networkx)
        self.create_gf()

        self.projection_data = {}

    def _getter(self):
        """
        Getter for graphframe. Returns the graphframe.
        """
        return self.gf

    def _setter(self, gf):
        """
        Setter for graphframe. Hooks the graphframe.
        """
        assert isinstance(gf, callflow.GraphFrame)

        self.gf = gf

    def create_gf(self):
        """
        Creates a graphframe using config and networkX grapg from hatchet graph.
        Each graphframe is tagged by a unique identifier. 
        e.g., here is the runName from config file or JSON.
        """
        if self.mode == "process":
            gf = callflow.GraphFrame.from_config(self.props, self.tag)
            self.gf = copy.deepcopy(gf)
        elif self.mode == "render":
            self.gf = callflow.GraphFrame.from_saved_files(self.process, self.tag)
    
    def process_gf(self):
        """
        # TODO: move the process functions to graphframe. 
        # I am not doing this now. Might be next commit. 
        Process graphframe to add properties depending on the format. 
        Current processing is supported for hpctoolkit and caliper. 
        """
        gf = self._getter()
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

        self._setter(process.gf)

    def group_gf(self, group_by="module"):
        """
        TODO: We have to do this using setter only. 
        Group the graphframe based on `group_by` parameter. 
        """
        group = Group(self.gf, group_by)

        assert isinstance(group.gf, callflow.GraphFrame)
        self.gf = group.gf

    def filter_gf(self, mode="single"):
        """
        TODO: We have to do this using setter only. 
        Filter the graphframe. 
        """
        gf = self.gf
        filter_res = Filter(
            gf,
            mode=mode,
            filter_by=self.props["filter_by"],
            filter_perc=self.props["filter_perc"],
        )
        assert isinstance(filter_res.gf, callflow.GraphFrame)
        self.gf = filter_res.gf

    def auxiliary(self, MPIBinCount=20, RunBinCount=20, process=True, write=True):
        datasets = self.props["dataset_names"]
        props = self.props
        EnsembleAuxiliary(
            self.gf, datasets, self.props, MPIBinCount, RunBinCount, process, write
        )

    def get_top_n_callsites_by_attr(self, count, sort_attr):
        """
        Returns an array of callsites (sorted by `sort_attr`)
        """
        xgroup_df = self.entire_df.groupby(["name"]).mean()
        sort_xgroup_df = xgroup_df.sort_values(by=[sort_attr], ascending=False)
        callsites_df = sort_xgroup_df.nlargest(count, sort_attr)
        return callsites_df.index.values.tolist()

    def read_gf(
        self, read_df=True, read_nxg=True, read_parameter=True
    ):
        """
        # Read a single dataset stored in .callflow directory.
        """

        LOGGER.info("Reading the dataset: {0}".format(self.tag))

        if read_df:
            df_file_name = gf_type + "_df.csv"
            df_file_path = os.path.join(self.dirname, self.tag, df_file_name)
            df = pd.read_csv(df_file_path)

            if df.empty:
                raise ValueError(f"{df_file_path} is empty.")

        if read_nxg:
            nxg_file_name = "nxg.json"
            nxg_file_path = os.path.join(self.dirname, self.tag, nxg_file_name)
            with open(nxg_file_path, "r") as nxg_file:
                graph = json.load(nxg_file)
            nxg = json_graph.node_link_graph(graph)
            assert nxg != None

        if read_parameter:
            parameters_filepath = os.path.join(self.dirname, self.tag, "env_params.txt")
            projection_data = {}
            for line in open(parameters_filepath, "r"):
                s = 0
                for num in line.strip().split(","):
                    split_num = num.split("=")
                    projection_data[split_num[0]] = split_num[1]

            assert projection_data != {}
            self.projection_data = projection_data

            self.gf = GraphFrame(dataframe=df)

    def write_gf(self, gf_type, write_df=True, write_graph=True, write_nxg=True):
        """
        # Write the dataset to .callflow directory.
        """
        # Get the save path.
        dirname = self.props["save_path"]

        gf = self.gf
        # dump the filtered dataframe to csv if write_df is true.
        if write_df:
            df_file_name = gf_type + "_df.csv"
            df_file_path = os.path.join(dirname, self.tag, df_file_name)
            gf.df.to_csv(df_file_path)

        # TODO: Writing fails.
        if write_nxg:
            nxg_file_name = gf_type + "_nxg.json"
            nxg_file_path = os.path.join(dirname, self.tag, nxg_file_name)
            nxg_data = json_graph.node_link_data(self.gf.nxg)
            with open(nxg_file_path, "w") as nxg_file:
                json.dump(nxg_data, nxg_file)

        if not write_graph:
            graph_filepath = os.path.join(dirname, self.tag, "hatchet_tree.txt")
            with open(graph_filepath, "a") as hatchet_graphFile:
                hatchet_graphFile.write(self.gf.tree(color=False))

    def write_similarity(self, datasets, states, type):
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
        all_data_filepath = os.path.join(self.props["save_path"], "auxiliary_data.json")
        LOGGER.info(f"[Read] {all_data_filepath}")
        with open(all_data_filepath, "r") as filter_graphFile:
            data = json.load(filter_graphFile)
        return data

    
    @staticmethod
    def _create_source_targets(self, path):
        module = ""
        edges = []

        for idx, callsite in enumerate(path):
            if idx == len(path) - 1:
                break

            source = sanitizeName(path[idx])
            target = sanitizeName(path[idx + 1])

            edges.append({"source": source, "target": target})
        return edges

    @staticmethod
    def _check_cycles(self, hierarchy, G):
        try:
            cycles = list(nx.find_cycle(self.hierarchy, orientation="ignore"))
        except:
            cycles = []

        return cycles

    @staticmethod
    def _remove_cycles(self, hierarchy, G, cycles):
        for cycle in cycles:
            source = cycle[0]
            target = cycle[1]
            print("Removing edge:", source, target)
            if source == target:
                print("here")
                G.remove_edge(source, target)
                G.remove_node(source)
                G.remove_node

            if cycle[2] == "reverse":
                print("Removing edge:", source, target)
                G.remove_edge(source, target)
        return G

    @staticmethod
    def _add_hierarchy_paths(self, hierarchy, df, path_name, filterTopCallsites=False):
        module_df = self.df.loc[self.df["module"] == self.module]
        if filterTopCallsites:
            group_df = module_df.groupby(["name"]).mean()
            f_group_df = group_df.loc[group_df[self.config.filter_by] > 500000]
            callsites = f_group_df.index.values.tolist()
            df = df[df["name"].isin(callsites)]

        paths = df[path_name].unique()
        for idx, path in enumerate(paths):
            if isinstance(path, float):
                return []
            path = make_tuple(path)
            source_targets = self.create_source_targets(path)
            for edge in source_targets:
                source = edge["source"]
                target = edge["target"]
                if not hierarchy.has_edge(source, target):
                    hierarchy.add_edge(source, target)

    def module_hierarchy(self, module=None):
        hierarchy = nx.DiGraph()
        node_paths_df = self.df.loc[self.df["module"] == self.module]

        if "component_path" not in self.df.columns:
            utils.debug("Error: Component path not defined in the df")

        with self.timer.phase("Add paths"):
            self._add_hierarchy_paths(hierarchy, node_paths_df, "component_path")

        cycles = self._check_cycles(hierarchy)
        while len(cycles) != 0:
            self.hierarchy = self._remove_cycles(hierarchy, cycles)
            cycles = self._check_cycles(hierarchy)
            print(f"cycles: {cycles}")

        return hierarchy

    def create_target_maps(self, dataset):
        self.target_df = {}
        self.target_modules = {}
        self.target_module_group_df = {}
        self.target_module_name_group_df = {}
        self.target_module_callsite_map = {}
        self.target_module_time_inc_map = {}
        self.target_module_time_exc_map = {}
        self.target_name_time_inc_map = {}
        self.target_name_time_exc_map = {}

        
        # Reduce the entire_df to respective target dfs.
        self.target_df[dataset] = self.entire_df.loc[self.entire_df["dataset"] == dataset]

        # Unique modules in the target run
        self.target_modules[dataset] = self.target_df[dataset]["module"].unique()

        # Group the dataframe in two ways.
        # 1. by module
        # 2. by module and callsite
        self.target_module_group_df[dataset] = self.target_df[dataset].groupby(["module"])
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

    def create_ensemble_maps(self):
        self.modules = self.entire_df["module"].unique()

        self.module_name_group_df = self.entire_df.groupby(["module", "name"])
        self.module_group_df = self.entire_df.groupby(["module"])
        self.name_group_df = self.entire_df.groupby(["name"])

        # Module map for ensemble {'module': [Array of callsites]}
        self.module_callsite_map = self.module_group_df["name"].unique().to_dict()

        # Inclusive time maps for the module level and callsite level.
        self.module_time_inc_map = self.module_group_df["time (inc)"].max().to_dict()
        self.name_time_inc_map = self.module_name_group_df["time (inc)"].max().to_dict()

        # Exclusive time maps for the module level and callsite level.
        self.module_time_exc_map = self.module_group_df["time"].max().to_dict()
        self.name_time_exc_map = self.module_name_group_df["time"].max().to_dict()

    def _remove_cycles_in_paths(self, path):
        ret = []
        moduleMapper = {}
        dataMap = {}

        if isinstance(path, float):
            return []
        path = make_list(path)
        for idx, elem in enumerate(path):
            callsite = elem.split("=")[1]
            module = elem.split("=")[0]
            if module not in dataMap:
                moduleMapper[module] = 0
                dataMap[module] = [
                    {"callsite": callsite, "module": module, "level": idx}
                ]
            else:
                flag = [p["level"] == idx for p in dataMap[module]]
                if np.any(np.array(flag)):
                    moduleMapper[module] += 1
                    dataMap[module].append(
                        {
                            "callsite": callsite,
                            "module": module + "=" + callsite,
                            "level": idx,
                        }
                    )
                else:
                    dataMap[module].append(
                        {"callsite": callsite, "module": module, "level": idx}
                    )
            ret.append(dataMap[module][-1])

        return ret


    def add_paths(self, path):
        pass

    def add_reveal_paths():
        pass

    def add_entry_callsite():
        pass

    def add_exit_callsite():
        pass

    def add_node_attributes(self):
        pass

    def add_edge_attribtues(self):
        pass
