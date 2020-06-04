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
import pandas as pd
import time

import callflow

LOGGER = callflow.get_logger(__name__)


class FilterHatchet:
    """
    Filter the graphframe.
    Input: State object, parameter to filterBy (could be inclusive/exclusive,
            filterPerc: user provided filter percentage (1-100))
    """

    def __init__(self, state, filterBy, filterPerc):
        self.state = state

        self.graph = state.new_entire_gf.graph
        self.df = state.new_entire_gf.df
        self.gf = state.new_entire_gf

        # self.df.set_index(['node', 'rank'], drop=False, inplace=True)

        # self.df = pd.MultiIndex.from_frame(self.df, names=['node', 'rank'])
        self.gf.dataframe = self.df

        self.filterBy = filterBy
        self.filterPercInDecimals = int(1) / 100
        # self.filterPercInDecimals = 0.001

        self.fgf = self.run()
        self.fgf = self.graft()

        # update df and graph after filtering.
        self.df = self.fgf.dataframe
        self.graph = self.fgf.graph

    def run(self):
        LOGGER.info("Filtering the graph.")
        t = time.time()
        if self.filterBy == "Inclusive":
            max_inclusive_time = utils.getMaxIncTime_from_gf(self.graph, self.df)
            filter_gf = self.gf.filter(
                lambda x: True
                if (x["time (inc)"] > self.filterPercInDecimals * max_inclusive_time)
                else False
            )
        elif filterBy == "Exclusive":
            max_exclusive_time = utils.getMaxExcTime_from_gf(self.graph, self.df)
            LOGGER.info("[Filter] By Exclusive time = {0})".format(max_exclusive_time))
            filter_gf = self.gf.filter(
                lambda x: True
                if (x["time"] >= self.filterPercInDecimals * max_exclusive_time)
                else False
            )
        else:
            LOGGER.warn("Not filtering.... Can take forever. Thou were warned")
            filter_gf = self.gf

        LOGGER.info(
            "[Filter] Removed {0} rows. (time={1})".format(
                self.gf.dataframe.shape[0] - filter_gf.dataframe.shape[0],
                time.time() - t,
            )
        )

        return filter_gf

    def graft(self):
        LOGGER.info("Squashing the graph.")
        t = time.time()
        fgf = self.fgf.squash()
        LOGGER.info(
            "[Squash] {1} rows in dataframe (time={0})".format(
                time.time() - t, fgf.dataframe.shape[0]
            )
        )
        return fgf
