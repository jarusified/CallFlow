##############################################################################
# Copyright (c) 2018-2019, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Callflowt.
# Created by Suraj Kesavan <kesavan1@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# For details, see: https://github.com/LLNL/Callflow
# Please also read the LICENSE file for the MIT License notice.
##############################################################################
import bisect
import random
from functools import wraps

import numpy as np
from scipy.stats import kurtosis, skew
from utils.df import sanitizeName, visModuleCallsiteName
from utils.hatchet import getNodeDictFromFrame, getPathListFromFrames
from utils.logger import log


def logger(func):
	@wraps(func)
	def tmp(*args, **kwargs):
		log.info("Preprocessing : {0}".format(func.__name__))
		return func(*args, **kwargs)

	return tmp


# Preprocess the dataframe
# Builder object
# Preprocess.add_X().add_Y().....
class PreProcess:
	def __init__(self, builder):
		self.gf = builder.gf
		self.df = builder.df
		self.graph = builder.graph

	class Builder(object):
		def __init__(self, state, gf_type="entire"):
			self.state = state

			self.callers = {}
			self.callees = {}
			self.frames = {}
			self.paths = {}
			self.hatchet_nodes = {}

			if gf_type == "filter":
				self.gf = state.gf
				self.df = state.df
				self.graph = state.entire_graph
			elif gf_type == "entire":
				self.gf = state.entire_gf
				self.df = state.entire_df
				self.graph = state.entire_graph

			# Logger Information
			self.cct_nodes = []
			self.callgraph_nodes = []
			self.supergraph_nodes = []
			self.unmapped_targets = []

			self.callgraph_nodes_np = np.array([])
			self.cct_nodes_np = np.array([])
			self.graphMapper()
			self.map = {}

		# def dfMapper(self):
		# 	ret = {}
		# 	for idx, row in self.df.iterrows():
		# 		node_df = self.state.lookup_with_node(row.node)
		# 		n_index = node_df["n_index"].tolist()
		# 		p_incTime = node_df[attr].tolist()
		# 		for idx in range(len(n_index)):
		# 			if n_index[idx] not in ret:
		# 				ret[n_index[idx]] = []
		# 			ret[n_index[idx]].append(p_incTime[idx])
		# 	return ret

		#################### Mapper functions ###############
		# def update_unmapped_target_nodes(self, source, target):
		# 	if source in self.unmapped_targets:
		# 		self.unmapped_targets.remove(source)
		# 	elif target not in set(self.unmapped_targets):
		# 		self.unmapped_targets.append(target)

		def convertFrameList(self, nodes):
			ret = []
			for node in nodes:
				ret.append(node.frame.get('name'))
			return ret

		def graphMapper(self):
			graph = self.graph

			for node in graph.traverse():
				node_dict = getNodeDictFromFrame(node.frame)

				if(node_dict['type'] == 'loop'):
					node_name = 'Loop@' + sanitizeName(node_dict['name'] + ':' + str(node_dict['line']))
				elif(node_dict['type'] == 'statement'):
					node_name = sanitizeName(node_dict['name']) + ":" + str(node_dict['line'])
				else:
				 	node_name = node_dict['name']

				node_paths = node.paths()
				self.paths[node_name] = node_paths
				self.callers[node_name] = self.convertFrameList(node.parents)
				self.callees[node_name] = self.convertFrameList(node.children)
				self.hatchet_nodes[node_name] = node

		def build(self):
			return PreProcess(self)

		# @logger
		# def add_hatchet_node(self):
		# 	self.raiseExceptionIfNodeCountNotEqual(self.hatchet_nodes.keys())
		# 	self.df["hatchet_node"] = self.df["name"].apply(
		# 		lambda node_name: self.hatchet_nodes[node_name]
		# 	)
		# 	return self

		# Add the path information from the node object
		@logger
		def add_path(self):
			self.raiseExceptionIfNodeCountNotEqual(self.paths)
			self.df["path"] = self.df["name"].apply(
				lambda node_name: getPathListFromFrames(self.paths[node_name])
			)
			return self

		# Imbalance percentage Series in the dataframe
		@logger
		def add_imbalance_perc(self):
			inclusive = {}
			exclusive = {}
			std_deviation_inclusive = {}
			std_deviation_exclusive = {}

			skewness_inclusive = {}
			skewness_exclusive = {}

			kurtosis_inclusive = {}
			kurtosis_exclusive = {}

			for node_name in self.df['name'].unique():
				node_df = self.df.loc[self.df['name'] == node_name]

				max_incTime = node_df['time'].mean()
				mean_incTime = node_df['time (inc)'].mean()

				max_excTime = node_df['time'].max()
				mean_excTime = node_df['time'].mean()

				if mean_incTime == 0.0:
					mean_incTime = 1.0

				inclusive[node_name] = (max_incTime - mean_incTime) / mean_incTime
				exclusive[node_name] = (max_excTime - mean_excTime) / mean_excTime

				std_deviation_inclusive[node_name] = np.std(node_df['time (inc)'].tolist(), ddof=1)
				std_deviation_exclusive[node_name] = np.std(node_df['time'].tolist(), ddof=1)

				skewness_inclusive[node_name] = skew(node_df['time (inc)'].tolist())
				skewness_exclusive[node_name] = skew(node_df['time'].tolist())

				kurtosis_inclusive[node_name] = kurtosis(node_df['time (inc)'].tolist())
				kurtosis_exclusive[node_name] = kurtosis(node_df['time'].tolist())

			self.df["imbalance_perc_inclusive"] = self.df['name'].apply(lambda name: inclusive[name])
			self.df["imbalance_perc_exclusive"] = self.df['name'].apply(lambda name: exclusive[name])

			self.df["std_deviation_inclusive"] = self.df['name'].apply(lambda name: std_deviation_inclusive[name])
			self.df["std_deviation_exclusive"] = self.df['name'].apply(lambda name: std_deviation_exclusive[name])

			self.df["skewness_inclusive"] = self.df['name'].apply(lambda name: skewness_inclusive[name])
			self.df["skewness_exclusive"] = self.df['name'].apply(lambda name: skewness_exclusive[name])

			self.df["kurtosis_inclusive"] = self.df['name'].apply(lambda name: kurtosis_inclusive[name])
			self.df["kurtosis_exclusive"] = self.df['name'].apply(lambda name: kurtosis_exclusive[name])

			return self

		@logger
		def add_callers_and_callees(self):
			self.df["callees"] = self.df["name"].apply(lambda node: self.callees[node] )
			self.df["callers"] = self.df["name"].apply(lambda node: self.callers[node] )

			return self

		@logger
		def add_show_node(self):
			self.map["show_node"] = {}
			self.df["show_node"] = self.df["name"].apply(lambda node: True)
			return self

		# @logger
		# def update_show_node(self, show_node_map):
		# 	self.map.show_node = show_node_map
		# 	self.df["show_node"] = self.df["node"].apply(
		# 		lambda node: show_node_map[str(node.df_index)]
		# 	)
		# 	return self

		# node_name is different from name in dataframe. So creating a copy of it.
		@logger
		def add_vis_node_name(self):
			self.module_group_df = self.df.groupby(['module'])
			self.module_callsite_map = self.module_group_df['name'].unique()

			self.name_group_df = self.df.groupby(['name'])
			self.callsite_module_map = self.name_group_df['module'].unique().to_dict()

			self.df["vis_node_name"] = self.df["name"].apply(lambda name: sanitizeName(self.callsite_module_map[name][0]) + '=' + name)
			return self

		@logger
		def add_node_name_hpctoolkit(self, node_name_map):
			self.df["node_name"] = self.df["name"].apply(
				lambda name: node_name_map[name]
			)
			return self

		@logger
		def add_module_name_hpctoolkit(self):
			self.df["module"] = self.df["module"].apply(
				lambda name: sanitizeName(name)
			)
			return self

		@logger
		def add_node_name_caliper(self, node_module_map):
			self.df['node_name'] = self.df['name'].apply(lambda name: name_module_map[name])

		@logger
		def add_module_name_caliper(self, module_map):
			self.df['module'] = self.df['name'].apply(lambda name: module_map[name])
			return self

		@logger
		def add_dataset_name(self):
			self.df["dataset"] = self.state.name
			return self

		def raiseExceptionIfNodeCountNotEqual(self, attr):
			map_node_count = len(attr.keys())
			df_node_count = len(self.df['name'].unique())
			print(f"Map contains: {map_node_count} callsites, graph contains: {df_node_count} callsites")
			if map_node_count != df_node_count:
				raise Exception(
					f"Unmatched Preprocessing maps: Map contains: {map_node_count} nodes, graph contains: {df_node_count} nodes"
				)

		@logger
		def logInformation(self):
			log.info(f"CCT node count : {len(self.cct_nodes)}")
			log.info(f"CallGraph node count: {len(self.callgraph_nodes)}")
			log.info(f"SuperGraph node count: {len(self.df['module'].unique())}")
			return self
