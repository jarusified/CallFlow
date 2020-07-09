/*******************************************************************************
 * Copyright (c) 2020, Lawrence Livermore National Security, LLC.
 * Produced at the Lawrence Livermore National Laboratory.
 *
 * Written by Suraj Kesavan <spkesavan@ucdavis.edu>.
 *
 * LLNL-CODE-740862. All rights reserved.
 *
 * This file is part of CallFlow. For details, see:
 * https://github.com/LLNL/CallFlow
 * Please also read the LICENSE file for the MIT License notice.
 ******************************************************************************/

import * as d3 from "d3";

export default {
	template: "<g id=\"tooltip_scatterplot\"></g>",
	name: "ToolTip",
	components: {},
	props: [],
	data: () => ({
		id: "",
		textCount: 0,
		textxOffset: 20,
		textyOffset: 20,
		textPadding: 13,
		offset: 10,
		fontSize: 12,
	}),
	sockets: {
		tooltip(data) {
			this.render(data);
		},
	},
	watch: {

	},

	mounted() { },
	methods: {
		init(id) {
			this.id = id;
			this.toolTipDiv = d3.select("#" + this.id)
				.append("svg")
				.attr("class", "toolTipSVG");

			this.toolTipG = this.toolTipDiv.append("g");
			this.height = document.getElementById(this.id).clientHeight / 10;
			this.halfWidth = document.getElementById(this.id).clientWidth / 2;
		},

		render(data, node) {
			this.clear();
			this.width = data.length * this.fontSize + 10 * this.fontSize;
			var svgScale = d3.scaleLinear().domain([2, 11]).range([50, 150]);
			this.mousePos = d3.mouse(d3.select("#" + this.id).node());
			this.mousePosX = this.mousePos[0];
			this.mousePosY = this.mousePos[1];
			this.toolTipG.attr("height", svgScale(10) + "px");
			this.toolTipRect = this.toolTipG
				.append("rect")
				.attrs({
					"class": "toolTipContent",
					"fill": "white",
					"stroke": "black",
					"rx": "10px",
					"fill-opacity": 1,
					"width": this.width,
					"height": this.height,
				})
				.attrs({
					"x": () => {
						if (this.mousePosX + this.halfWidth > document.getElementById(this.id).clientWidth - 25) {
							return (this.mousePosX - this.width) + "px";
						}
						return (this.mousePosX) + "px";

					},
					"y": () => {
						return (this.mousePosY) + "px";
					}
				});
			this.node = node;
			this.data = data;
			this.processes();
		},

		addText(text) {
			this.textCount += 1;
			this.toolTipText = this.toolTipG
				.append("text")
				.style("font-family", "sans-serif")
				.style("font-size", this.fontSize)
				.attrs({
					"class": "toolTipContent",
					"x": () => {
						if (this.mousePosX + this.halfWidth > document.getElementById(this.id).clientWidth - 25) {
							return (this.mousePosX - this.width + this.offset) + "px";
						}
						return (this.mousePosX) + this.offset + "px";

					},
					"y": () => {
						return (this.mousePosY) + 2 * this.offset + "px";
					}
				})
				.text(text);
		},

		processes() {
			let self = this;
			this.addText("Processes (MPI ranks): " + this.data);

		},

		clear() {
			this.textCount = 0;
			d3.selectAll(".toolTipContent").remove();
		},

	}
};