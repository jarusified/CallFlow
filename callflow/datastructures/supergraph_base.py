import networkx as nx
from callflow import Dataset


class SuperGraph(Dataset):
    def __init__(self, props, tag):
        super().__init__(props, tag)

        # TODO: Set the graphframe through the create function
        self.gf = self.create()

    def create(self):
        pass 
    
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

    def add_reveal_paths()
        pass

    def add_entry_callsite():
        pass

    def add_exit_callsite():
        pass

    def add_node_attributes(self):
        pass

    def add_edge_attribtues(self):
        pass
