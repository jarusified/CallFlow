import tpl from '../html/icicle.html'
import * as d3 from 'd3'

export default {
	name: 'Icicle',
	template: tpl,
	components: {

	},
	props: [

	],
	data: () => ({
		id: 'component_graph_view',
		margin: {
			top: 10,
			right: 10,
			bottom: 30,
			left: 40,
		},
		level: [0, 4],
	}),

	watch: {

	},

	sockets: {
		hierarchy(data) {
			console.log(data)
			this.start(data)
		}
	},

	methods: {
		init() {
			this.width = document.getElementById(this.id).clientWidth
			this.height = window.innerHeight / 2 - 50

			this.boxWidth = this.width - this.margin.right - this.margin.left;
			this.boxHeight = this.height - this.margin.top - this.margin.bottom - 20;
			this.icicleOffset = Math.floor(this.boxHeight / 3);
			this.icicleHeight = this.boxHeight - this.histogramOffset;
			this.icicleWidth = this.boxWidth;

			this.icicleSVGid = 'component_graph_view_svg'
			this.setupSVG()
		},

		setupSVG() {
			this.icicleSVG = d3.select('#' + this.id)
				.append('svg')
				.attrs({
					"id": this.icicleSVGid,
					"width": this.boxWidth + this.margin.right + this.margin.left,
					"height": this.boxHeight + this.margin.top + this.margin.bottom,
				})
				.append('g')
				.attrs({
					'transform': `translate(${this.margin.left},${this.margin.top})`
				})
		},

		start(data) {
			let path_hierarchy_format = []
			let nodes = data.nodes
			for (let i = 0; i < nodes.length; i += 1) {
				path_hierarchy_format[i] = [];
				path_hierarchy_format[i].push(nodes[i]['component_path']);
				path_hierarchy_format[i].push(nodes[i]['time (inc)']);
				path_hierarchy_format[i].push(nodes[i]['time']);
				path_hierarchy_format[i].push(nodes[i]['imbalance_perc']);
			}
			console.log(path_hierarchy_format)
			const json = this.buildHierarchy(path_hierarchy_format);
			console.log(json)
			this.drawIcicles(json);
		},

		start_from_df(data) {
			const path = hierarchy['component_path']
			const inc_time = hierarchy['time (inc)']
			const exclusive = hierarchy['time']
			const imbalance_perc = hierarchy['imbalance_perc']
			// const exit = hierarchy.exit;
			// const component_path = hierarchy.component_path;
			console.log(path)
			const path_hierarchy_format = [];
			for (const i in path) {
				if (path.hasOwnProperty(i)) {
					path_hierarchy_format[i] = [];
					path_hierarchy_format[i].push(path[i]);
					path_hierarchy_format[i].push(inc_time[i]);
					path_hierarchy_format[i].push(exclusive[i]);
					path_hierarchy_format[i].push(imbalance_perc[i]);
					// path_hierarchy_format[i].push(exit[i]);
					// path_hierarchy_format[i].push(component_path[i]);
				}
			}
			console.log(path_hierarchy_format)
			const json = this.buildHierarchy(path_hierarchy_format);
			console.log(json)
			this.drawIcicles(json);
		},

		buildHierarchy(csv) {
			const root = {
				name: 'root',
				children: []
			};
			for (let i = 0; i < csv.length; i++) {
				const sequence = csv[i][0];
				const inc_time = csv[i][1];
				const exclusive = csv[i][2];
				const imbalance_perc = csv[i][3];
				// const exit = csv[i][4];
				// const component_path = csv[i][5];
				const parts = sequence;
				let currentNode = root;
				for (let j = 0; j < parts.length; j++) {
					const children = currentNode.children;
					const nodeName = parts[j];
					var childNode;
					if (j + 1 < parts.length) {
						// Not yet at the end of the sequence; move down the tree.
						let foundChild = false;
						for (let k = 0; k < children.length; k++) {
							if (children[k].name == nodeName) {
								childNode = children[k];
								foundChild = true;
								break;
							}
						}
						// If we don't already have a child node for this branch, create it.
						if (!foundChild) {
							childNode = {
								name: nodeName,
								children: []
							};
							children.push(childNode);
						}
						currentNode = childNode;
					} else {
						// Reached the end of the sequence; create a leaf node.
						childNode = {
							name: nodeName,
							weight: inc_time,
							exclusive,
							imbalance_perc,
							// exit,
							// component_path,
							children: [],
						};
						children.push(childNode);
					}
				}
			}
			return root;
		},
		clearIcicles(view) {
			$('#iciclehierarchySVG').remove();
		},

		drawIcicles(view, json) {
			let direction = view.icicleDirection;
			let attr = view.icicleColorByAttr;
			if (view.hierarchy != undefined) {
				clearIcicles(view);
			}
			// Total size of all segments; we set this later, after loading the data
			let totalSize = 0;
			// eslint-disable-next-line no-param-reassign
			view.hierarchy = d3.select('#component_graph_view').append('svg')
				.attr('width', this.width)
				.attr('height', this.height)
				.attr('id', 'iciclehierarchySVG')
				.append('g')
				.attr('id', 'container');

			let root = d3.hierarchy(json, getChild)
				.sum((d) => {
					return 1
				})
				.sort(null)

			const partition = d3.partition()
				.size([this.width, this.height])
			// .value(d => d.weight);

			// Basic setup of page elements.
			// initializeBreadcrumbTrail();
			//  drawLegend();
			d3.select('#togglelegend').on('click', this.toggleLegend);

			// Bounding rect underneath the chart, to make it easier to detect
			// when the mouse leaves the parent g.
			view.hierarchy.append('svg:rect')
				.attr('width', () => {
					if (direction == 'LR') return this.boxHeight;
					return this.width;
				})
				.attr('height', () => {
					if (direction == 'LR') return this.width - 50;
					return this.height - 50;
				})
				.style('opacity', 0)

			partition(root)

			// For efficiency, filter nodes to keep only those large enough to see.
			const nodes = partition.nodes(json)
				.filter(d => (d.dx > 0.5));

			const node = view.hierarchy.data([json]).selectAll('.icicleNode')
				.data(nodes)
				.enter()
				.append('rect')
				.attr('class', 'icicleNode')
				.attr('x', (d) => {
					if (direction == 'LR') {
						return d.y;
					}
					return d.x;
				})
				.attr('y', (d) => {
					if (direction == 'LR') {
						return d.x;
					}
					return d.y;
				})
				.attr('width', (d) => {
					if (direction == 'LR') {
						return d.dy;
					}
					return d.dx;
				})
				.attr('height', (d) => {
					if (direction == 'LR') {
						return d.dx;
					}
					return d.dy;
				})
				.style('fill', (d) => {
					const color = view.color.getColor(d);
					if (color._rgb[0] == 204) {
						return '#7A000E';
					}
					return color;
				})
				.style('stroke', () => '#0e0e0e')
				.style('stroke-width', d => '1px')
				.style('opacity', (d) => {
					if (d.exit) {
						return 0.5;
					}
					return 1;
				})
				.on('mouseover', mouseover);

			const text = view.hierarchy.data([json]).selectAll('.icicleText')
				.data(nodes)
				.enter()
				.append('text')
				.attr('class', 'icicleText')
				.attr('transform', (d) => {
					if (direction == 'LR') {
						return 'rotate(90)';
					}
					return 'rotate(0)';
				})
				.attr('x', (d) => {
					if (direction == 'LR') {
						return d.y * len(d.component_path);
					}
					return d.x + 15;
				})
				.attr('y', (d) => {
					if (direction == 'LR') {
						return d.x;
					}
					return d.y + 15;
				})
				.attr('width', (d) => {
					if (direction == 'LR') {
						return d.dy / 2;
					}
					return d.dx / 2;
				})
				.text((d) => {
					const textTruncForNode = 10;
					if (d.dy < 10 || d.dx < 50) {
						return '';
					}
					return d.name.trunc(textTruncForNode);
				});


			// Add the mouseleave handler to the bounding rect.
			d3.select('#container').on('mouseleave', mouseleave);

			// Get total size of the tree = value of root node from partition.
			// eslint-disable-next-line no-underscore-dangle
			totalSize = node.node().__data__.value;

			// Fade all but the current sequence, and show it in the breadcrumb trail.
			function mouseover(d) {
				const percentage = (100 * d.value / totalSize).toPrecision(3);
				let percentageString = `${percentage}%`;
				if (percentage < 0.1) {
					percentageString = '< 0.1%';
				}

				const sequenceArray = getAncestors(d);
				// updateBreadcrumbs(sequenceArray, percentageString);

				// Fade all the segments.
				d3.selectAll('.icicleNode')
					.style('opacity', 0.3);

				// Then highlight only those that are an ancestor of the current segment.
				view.hierarchy.selectAll('.icicleNode')
					// eslint-disable-next-line no-shadow
					.filter(node => (sequenceArray.indexOf(node) >= 0))
					.style('opacity', 1);
			}

			// Restore everything to full opacity when moving off the visualization.
			function mouseleave() {
				// Hide the breadcrumb trail
				d3.select('#trail')
					.style('visibility', 'hidden');

				// Deactivate all segments during transition.
				d3.selectAll('.icicleNode').on('mouseover', null);

				// Transition each segment to full opacity and then reactivate it.
				d3.selectAll('.icicleNode')
					.transition()
					.duration(1000)
					.style('opacity', 1)
					.each('end', function () {
						d3.select(this).on('mouseover', mouseover);
					});
			}
		},

		// Given a node in a partition layout, return an array of all of its ancestor
		// nodes, highest first, but excluding the root.
		getAncestors(node) {
			const path = [];
			let current = node;
			while (current.parent) {
				path.unshift(current);
				current = current.parent;
			}
			return path;
		},

		initializeBreadcrumbTrail() {
			// Add the svg area.
			const width = $('#component_graph_view').width();
			const trail = d3.select('#sequence').append('svg:svg')
				.attr('width', width)
				.attr('height', 50)
				.attr('id', 'trail');
			// Add the label at the end, for the percentage.
			trail.append('svg:text')
				.attr('id', 'endlabel')
				.style('fill', '#000');
		},

		// Generate a string that describes the points of a breadcrumb polygon.
		breadcrumbPoints(i) {
			const points = [];
			points.push('0,0');
			points.push(`${b.w},0`);
			points.push(`${b.w + b.t},${b.h / 2}`);
			points.push(`${b.w},${b.h}`);
			points.push(`0,${b.h}`);
			if (i > 0) { // Leftmost breadcrumb; don't include 6th vertex.
				points.push(`${b.t},${b.h / 2}`);
			}
			return points.join(' ');
		},

		// Update the breadcrumb trail to show the current sequence and percentage.
		updateBreadcrumbs(nodeArray, percentageString) {
			// Data join; key function combines name and depth (= position in sequence).
			const g = d3.select('#trail')
				.selectAll('g')
				.data(nodeArray, d => d.name + d.depth);

			// Add breadcrumb and label for entering nodes.
			const entering = g.enter().append('svg:g');

			entering.append('svg:polygon')
				.attr('points', breadcrumbPoints)
				.style('fill', () => '#f1f1f1');

			entering.append('svg:text')
				.attr('x', (b.w + b.t) / 2)
				.attr('y', b.h / 2)
				.attr('dy', '0.35em')
				.attr('text-anchor', 'middle')
				.text(d => d.name);

			// Set position for entering and updating nodes.
			g.attr('transform', (d, i) => `translate(${i * (b.w + b.s)}, 0)`);

			// Remove exiting nodes.
			g.exit().remove();

			// Now move and update the percentage at the end.
			d3.select('#trail').select('#endlabel')
				.attr('x', (nodeArray.length + 0.5) * (b.w + b.s))
				.attr('y', b.h / 2)
				.attr('dy', '0.35em')
				.attr('text-anchor', 'middle')
				.text(percentageString);

			// Make the breadcrumb trail visible, if it's hidden.
			d3.select('#trail')
				.style('visibility', '');
		},

		toggleLegend() {
			const legend = d3.select('#legend');
			if (legend.style('visibility') == 'hidden') {
				legend.style('visibility', '');
			} else {
				legend.style('visibility', 'hidden');
			}
		},
	}
}