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
from logger import log
import os
import hatchet as ht
from logger import log

class Create:
    """
	Creates a graph frame.
	Input : config variable, and dataset name
	Output : State object containing components of graphframe as separate object variables.
	"""

    def __init__(self, config, name):
        log.info(f"Creating graphframes for run: {name}")
        self.config = config
        self.name = name
        self.run()

    def run(self):
        print(self.config.callflow_path)
        data_path = self.config.data_path[self.name]
        print(data_path)

        if self.config.format[self.name] == "hpctoolkit":
            self.gf = ht.GraphFrame.from_hpctoolkit(data_path)
        elif self.config.format[self.name] == "caliper":
            self.gf = ht.GraphFrame.from_caliper(data_path)

        self.df = self.gf.dataframe
        self.graph = self.gf.graph
