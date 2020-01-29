/** *****************************************************************************
 * Copyright (c) 2017, Lawrence Livermore National Security, LLC.
 * Produced at the Lawrence Livermore National Laboratory.
 *
 * Written by Huu Tan Nguyen <htpnguyen@ucdavis.edu>.
 *
 * LLNL-CODE-740862. All rights reserved.
 *
 * This file is part of CallFlow. For details, see:
 * https://github.com/LLNL/CallFlow
 * Please also read the LICENSE file for the MIT License notice.
 ***************************************************************************** */

import tpl from '../../html/callgraph/miniHistograms.html'
import * as d3 from 'd3'
import 'd3-selection-multi'

export default {
    template: tpl,
    name: 'MiniHistograms',
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
        selectedColorBy: "Inclusive",
        padding: {
            top: 0, left: 0, right: 0, bottom: 10
        },
        nodeScale: 0.99,
        data: null,
        id: '',
        nodes: null,
        edges: null,
    }),

    mounted() {
        this.id = 'minihistogram-overview-' + this._uid
    },

    methods: {
        init(graph, view) {
            this.nodeMap = graph.nodeMap
            this.nodes = graph.nodes
            this.links = graph.links
            this.view = view
            for(const [idx, callsite] of Object.entries(graph.nodes)){
                let callsite_module = callsite.module
                let callsite_name = callsite.name
                console.log(callsite_module, callsite_name)
                this.render(callsite_name, callsite_module)
            }
        },

        array_unique(arr) {
            return arr.filter(function (value, index, self) {
                return self.indexOf(value) === index;
            })
        },

        dataProcess(data) {
            let attr_data = {}

            if (this.selectedColorBy == 'Inclusive') {
                attr_data = data['hist_time (inc)']
            } else if (this.selectedColorBy == 'Exclusive') {
                attr_data = data['hist_time']
            } else if (this.selectedColorBy == 'Imbalance') {
                attr_data = data['hist_imbalance']
            }

            return [attr_data['x'], attr_data['y']];
        },

        clear() {
            d3.selectAll('#histobars').remove()
        },

        histogram(data, node_dict, type) {
            const processData = this.dataProcess(data)
            let xVals = processData[0]
            let freq = processData[1]

            let color = ''
            if (type == 'ensemble') {
                color = this.$store.color.ensemble
            }
            else if (type == 'target') {
                color = this.$store.color.target
            }

            if (type == 'ensemble') {
                this.minimapXScale = d3.scaleBand()
                    .domain(xVals)
                    .rangeRound([0, this.$parent.nodeWidth])

                this.minimapYScale = d3.scaleLinear()
                    .domain([0, d3.max(freq)])
                    .range([this.$parent.ySpacing, 0]);

            }

            for (let i = 0; i < freq.length; i += 1) {
                d3.select('#' + this.id)
                    .append('rect')
                    .attrs({
                        'id': 'histobars',
                        'class': 'histogram-bar ' + type,
                        'width': () => this.minimapXScale.bandwidth(),
                        'height': (d) => {
                            return (this.$parent.nodeWidth) - this.minimapYScale(freq[i])
                        },
                        'x': (d) => node_dict.x + this.minimapXScale(xVals[i]),
                        'y': (d) => node_dict.y + this.minimapYScale(freq[i]),
                        'stroke-width': '0.2px',
                        'stroke': 'black',
                        'fill': color,
                    })
            }
        },

        render(callsite_name, callsite_module) {
            console.log(callsite_module)
            console.log(this.$store.modules[this.$store.selectedTargetDataset])
            let node_dict = this.nodes[this.nodeMap[callsite_name]]
            let ensemble_callsite_data = this.$store.modules['ensemble'][callsite_module]
            let target_callsite_data = this.$store.modules[this.$store.selectedTargetDataset][callsite_module]

            console.log(target_callsite_data)

            this.histogram(ensemble_callsite_data, node_dict, 'ensemble')
            this.histogram(target_callsite_data, node_dict, 'target')
        }
    }
}