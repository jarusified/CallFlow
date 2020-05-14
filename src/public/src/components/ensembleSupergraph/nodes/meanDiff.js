import tpl from '../../../html/ensembleSupergraph/node.html'
import * as d3 from 'd3'
import * as utils from '../../utils'

export default {
    template: tpl,
    name: 'MeanGradients',
    components: {},

    data: () => ({
        strokeWidth: 7,
        id: 'mean-gradients'
    }),

    methods: {
        init(nodes, svg) {
            this.nodes = nodes
            this.svg = svg

            this.ensemble_module_data = this.$store.modules['ensemble']
            this.ensemble_callsite_data = this.$store.callsites['ensemble']

            this.colorScale()
            this.gradients()
            this.visualize()
        },

        colorScale() {
            let hist_min = 0
            let hist_max = 0
            for (let node of this.nodes) {
                if (node.type == 'super-node') {
                    hist_min = Math.min(hist_min, this.ensemble_module_data[node.module][this.$store.selectedMetric]['gradients']['hist']['y_min'])
                    hist_max = Math.max(hist_max, this.ensemble_module_data[node.module][this.$store.selectedMetric]['gradients']['hist']['y_max'])
                }
                else if (node.type == 'component-node') {
                    hist_min = Math.min(hist_min, this.ensemble_callsite_data[node.name][this.$store.selectedMetric]['gradients']['hist']['y_min'])
                    hist_max = Math.max(hist_max, this.ensemble_callsite_data[node.name][this.$store.selectedMetric]['gradients']['hist']['y_max'])
                }
            }
            this.$store.binColor.setColorScale(hist_min, hist_max, this.$store.selectedDistributionColorMap, this.$store.selectedColorPoint)
            this.$parent.$parent.$refs.EnsembleColorMap.updateWithMinMax('bin', hist_min, hist_max)
        },

        meanDiffRectangle(diff) {
            let self = this
            let mean_diff = {}
            let max_diff = 0
            let min_diff = 0
            for (let i = 0; i < diff.length; i += 1) {
                let d = diff[i]['mean_diff']
                let callsite = diff[i]['name']
                mean_diff[callsite] = d
                max_diff = Math.max(d, max_diff)
                min_diff = Math.min(d, min_diff)
            }

            // Transition
            this.nodes.selectAll('.callsite-rect')
                .data(this.graph.nodes)
                .transition()
                .duration(this.transitionDuration)
                .attrs({
                    'opacity': d => {
                        return 1;
                    },
                    'height': d => {
                        if (d.id == "LeapFrog") {
                            return 352.328692
                        }
                        else {
                            return d.height;
                        }
                    },
                })
                .style('stroke', (d) => {
                    return 1;
                })
                .style("fill", (d, i) => {
                    let color = d3.rgb(this.$store.meanDiffColor.getColorByValue((mean_diff[d.module])))
                    return color
                })
        },

        visualize() {
            this.svg.selectAll('rect')
                .data(this.nodes)
                .transition()
                .duration(this.transitionDuration)
                .attrs({
                    'opacity': d => {
                        if (d.type == "intermediate") {
                            return 0.0
                        }
                        else {
                            return 1.0;
                        }
                    },

                })
                .style('stroke', (d) => {
                    let runtimeColor = ''
                    if (d.type == "intermediate") {
                        runtimeColor = this.$store.color.ensemble
                    }
                    else if (d.type == 'component-node') {
                        if (this.$store.callsites[this.$store.selectedTargetDataset][d.id] != undefined) {
                            runtimeColor = d3.rgb(this.$store.color.getColor(d));
                        }
                        else {
                            runtimeColor = this.$store.color.ensemble
                        }
                    }
                    else if (d.type == 'super-node') {
                        if (this.$store.modules[this.$store.selectedTargetDataset][d.id] != undefined) {
                            runtimeColor = d3.rgb(this.$store.color.getColor(d));
                        }
                        else {
                            runtimeColor = this.$store.color.ensemble
                        }
                    }
                    return runtimeColor
                })
                .style('stroke-width', (d) => {
                    if (d.type == "intermediate") {
                        return 1
                    }
                    else {
                        return this.stroke_width;
                    }
                })
                .style("fill", (d, i) => {
                    if (d.type == "intermediate") {
                        return this.$store.color.target
                    }
                    else if (d.type == 'super-node') {
                        if (this.$store.modules[this.$store.selectedTargetDataset][d.id] == undefined) {
                            return this.intermediateColor
                        }
                        else {
                            return "url(#mean-gradient" + d.client_idx + ")"
                        }
                    }
                    else if (d.type == 'component-node') {
                        if (this.$store.callsites[this.$store.selectedTargetDataset][d.name] == undefined) {
                            return this.intermediateColor
                        }
                        else {
                            return "url(#mean-gradient" + d.client_idx + ")"
                        }
                    }
                })
        },

        clear() {
        },
    }
}