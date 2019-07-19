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
import numpy as np

class splitRank:
    def __init__(self, state, ids):
        self.graph = state.graph
        self.df = state.df
        self.entire_df = state.entire_df
        self.ids = ids
        self.other_ids = self.find_other_ids()
        print(self.other_ids)

    def find_other_ids(self):
        unique_ids = list(self.entire_df['rank'].unique())
        print(unique_ids, self.ids)

        ret = [ids for ids in unique_ids if np.int64(ids) not in self.ids]
        return ret                                                                            