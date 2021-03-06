/** 
 * Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
 * CallFlow Project Developers. See the top-level LICENSE file for details.
 * 
 * SPDX-License-Identifier: MIT
 */

<template>
	<g :id="id"></g>
</template>

<script>
import * as d3 from "d3";
import "d3-selection-multi";

export default {
	name: "MiniHistograms",
	components: {},
	props: [],
	data: () => ({
		view: {},
		xScale: [],
		yScale: [],
		vals: [],
		freq: {},
		data: [],
		minimapXScale: null,
		minimapYScale: null,
		padding: {
			top: 0, left: 0, right: 0, bottom: 10
		},
		nodeScale: 0.99,
		id: "",
		nodes: null,
		edges: null,
		offset: 7,
		bandWidth: 0,
	}),

	mounted() {
		this.id = "minihistogram-overview";
	},

	methods: {
		init(graph, view) {
			this.nodeMap = graph.nodeMap;
			this.nodes = graph.nodes;
			this.links = graph.links;
			this.view = view;
			this.target_module_data = this.$store.modules[this.$store.selectedTargetDataset];
			this.target_callsite_data = this.$store.callsites[this.$store.selectedTargetDataset];

			for (const node of this.nodes) {
				let module = node.module;
				let callsite = node.name;

				if (node.type == "super-node" && this.target_module_data[module] != undefined) {
					let data = this.target_module_data[module][this.$store.selectedMetric]["prop_histograms"][this.$store.selectedProp];
					this.render(data, module);
				}
				else if (node.type == "component-node" && this.target_callsite_data[callsite] != undefined) {

					let data = this.target_callsite_data[callsite][this.$store.selectedMetric]["prop_histograms"][this.$store.selectedProp];
					this.render(data, callsite);
				}
			}
		},

		array_unique(arr) {
			return arr.filter(function (value, index, self) {
				return self.indexOf(value) === index;
			});
		},

		clear() {
			this.bandWidth = 0;
			d3.selectAll("#histobars").remove();
		},

		histogram(data, node_dict, type) {
			let color = "";
			let xVals = [], freq = [];
			if (type == "ensemble") {
				color = this.$store.distributionColor.ensemble;
				xVals = data["ensemble"].x;
				freq = data["ensemble"].y;
			}
			else if (type == "target" || type == "single") {
				if (type == "target")
					color = this.$store.distributionColor.target;
				else if (type == "single")
					color = this.$store.runtimeColor.intermediate;
				xVals = data["target"].x;
				freq = data["target"].y;
			}

			if (this.$store.selectedScale == "Linear") {
				this.minimapYScale = d3.scaleLinear()
					.domain([0, d3.max(freq)])
					.range([this.$parent.ySpacing - 10, 0]);
			}
			else if (this.$store.selectedScale == "Log") {
				this.minimapYScale = d3.scaleLog()
					.domain([0.1, d3.max(freq)])
					.range([this.$parent.ySpacing, 0]);
			}
			this.minimapXScale = d3.scaleBand()
				.domain(xVals)
				.rangeRound([0, this.$parent.nodeWidth]);
			this.bandWidth = this.minimapXScale.bandwidth();

			for (let i = 0; i < freq.length; i += 1) {
				d3.select("#" + this.id)
					.append("rect")
					.attrs({
						"id": "histobars",
						"class": "histogram-bar-" + type,
						"width": () => this.bandWidth,
						"height": (d) => {
							return this.$parent.nodeWidth - this.minimapYScale(freq[i]);
						},
						"x": (d) => {
							return node_dict.x + this.minimapXScale(xVals[i]);
						},
						"y": (d) => node_dict.y + this.minimapYScale(freq[i]) + this.offset,
						"stroke-width": "0.2px",
						"stroke": "black",
						"fill": color,
					});
			}
		},

		render(data, node) {
			let node_dict = this.nodes[this.nodeMap[node]];
			if (this.$store.selectedMode == "Ensemble") {
				this.histogram(data, node_dict, "ensemble");
				if (this.$store.showTarget && this.$store.comparisonMode == false) {
					this.histogram(data, node_dict, "target");
				}
			}
			else if (this.$store.selectedMode == "Single") {
				this.histogram(data, node_dict, "single");
			}
		}
	}
};
</script>