import * as d3 from 'd3'
import * as utils from '../../utils'

export default {
    template: '<g :id="id"></g>',
    name: 'MeanGradients',
    components: {},

    data: () => ({
        strokeWidth: 7,
        id: 'mean-gradients'
    }),

    methods: {
        init(nodes, svg) {
            this.nodes = nodes

            this.process(data)
            this.gradients()
            this.visualize()
        },

        process(data) {
            this.renderZeroLine = {}

            this.rank_min = 0
            this.rank_max = 0
            this.mean_min = 0
            this.mean_max = 0
            this.mean_diff_min = 0
            this.mean_diff_max = 0

            for (let i = 0; i < data.length; i += 1) {
                if (this.$store.selectedMetric == 'Inclusive') {
                    this.rank_min = Math.min(this.rank_min, data[i]['hist']['y_min'])
                    this.rank_max = Math.max(this.rank_max, data[i]['hist']['y_max'])
                    this.mean_min = Math.min(this.mean_min, data[i]['hist']['x_min'])
                    this.mean_max = Math.max(this.mean_max, data[i]['hist']['x_max'])
                    this.mean_diff_min = Math.min(this.mean_diff_min, data[i]['mean_diff'])
                    this.mean_diff_max = Math.max(this.mean_diff_max, data[i]['mean_diff'])
                }
                else if (this.$store.selectedMetric == 'Exclusive') {
                    this.rank_min = Math.min(this.rank_min, data[i]['hist']['y_min'])
                    this.rank_max = Math.max(this.rank_max, data[i]['hist']['y_max'])
                    this.mean_min = Math.min(this.mean_min, data[i]['hist']['x_min'])
                    this.mean_max = Math.max(this.mean_max, data[i]['hist']['x_max'])
                    this.mean_diff_min = Math.min(this.mean_diff_min, data[i]['mean_diff'])
                    this.mean_diff_max = Math.max(this.mean_diff_max, data[i]['mean_diff'])
                }
            }


        },

        colorScale() {
            let max_diff = Math.max(Math.abs(this.mean_diff_min), Math.abs(this.mean_diff_max))

            this.$store.meanDiffColor.setColorScale(this.mean_diff_min, this.mean_diff_max, this.$store.selectedDistributionColorMap, this.$store.selectedColorPoint)
            this.$parent.$refs.EnsembleColorMap.updateWithMinMax('meanDiff', this.mean_diff_min, this.mean_diff_max)

            this.meanDiffRectangle(data)
        },

        visualize(diff) {
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