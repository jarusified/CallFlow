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

import callflow

LOGGER = callflow.get_logger(__name__)

from callflow.timer import Timer
from callflow import Dataset
from callflow.utils import (
    getMaxExcTime,
    getMinExcTime,
    getMaxIncTime,
    getMinIncTime,
)

from callflow import CCT, SuperGraph, BaseCallFlow

from callflow.modules import (
    SingleAuxiliary,
    RankHistogram,
    MiniHistogram,
    RuntimeScatterplot,
    FunctionList,
)


class SingleCallFlow(BaseCallFlow):
    def __init__(self, config=None, process=False):
        super(SingleCallFlow, self).__init__(config, process)

    # --------------------------------------------------------------------------
    def _process_datasets(self):
        dataset_name = self.props["dataset_names"][0]
        dataset = Dataset(self.props, dataset_name)
        LOGGER.info("#########################################")
        LOGGER.info(f"Run: {dataset_name}")
        LOGGER.info("#########################################")

        # Create each graphframe.
        dataset.create_gf()

        # Process each graphframe.
        dataset.process_gf(gf_type="entire")

        # Filter by inclusive or exclusive time.
        dataset.filter_gf(mode="single")

        # Group by module.
        dataset.group_gf(gf_type="filter", group_by="module")

        dataset.write_gf("entire")

    def _read_datasets(self):
        dataset_name = self.props["dataset_names"][0]
        dataset = Dataset(self.props, dataset_name)
        dataset.read_gf(gf_type="entire", read_parameter=self.props["read_parameter"])
        return dataset

    def _request(self, action):
        LOGGER.info("[Single Mode]", action)
        action_name = action["name"]

        if action_name == "init":
            return self.props

        if "groupBy" in action:
            LOGGER.info("Grouping by: {0}".format(action["groupBy"]))
        else:
            action["groupBy"] = "name"

        dataset = action["dataset"]
        state = self.states[dataset]

        LOGGER.info("The selected Dataset is {0}".format(dataset))

        # Compare against the different operations
        if action_name == "reset":
            datasets = [dataset]
            self.reProcess = True
            self.states = self.pipeline(
                datasets, action["filterBy"], action["filterPerc"]
            )
            self.reProcess = False
            self.states = self.pipeline(datasets)
            return {}

        elif action_name == "auxiliary":
            auxiliary = Auxiliary(
                self.states[action["dataset"]],
                binCount=action["binCount"],
                dataset=action["dataset"],
                config=self.config,
            )
            return auxiliary.result

        elif action_name == "supergraph":
            self.states[dataset].g = SuperGraph(
                self.states, dataset, "group_path", construct_graph=True, add_data=True
            ).g
            return self.states[dataset].g

        elif action_name == "mini-histogram":
            minihistogram = MiniHistogram(state)
            return minihistogram.result

        elif action_name == "cct":
            graph = CCT(
                self.states[action["dataset"]], action["functionsInCCT"], self.config
            )
            return graph.g

        elif action_name == "function":
            functionlist = FunctionList(state, action["module"], action["nid"])
            return functionlist.result

    # --------------------------------------------------------------------------
