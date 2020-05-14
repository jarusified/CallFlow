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

        gradients() {
            let method = 'hist'
            for (let i = 0; i < data.length; i += 1) {
                let d = data[i]
                var defs = d3.select('#ensemble-supergraph-overview')
                    .append("defs");

                this.diffGradient = defs.append("linearGradient")
                    .attrs({
                        "id": "diff-gradient-" + this.nidNameMap[d.name],
                        "class": 'linear-gradient'
                    })

                this.diffGradient
                    .attrs({
                        "x1": "0%",
                        "y1": "0%",
                        "x2": "0%",
                        "y2": "100%"
                    })

                let min_val = d[method]['y_min']
                let max_val = d[method]['y_max']

                let grid = d[method]['x']
                let val = d[method]['y']

                for (let i = 0; i < grid.length; i += 1) {
                    let x = (i + i + 1) / (2 * grid.length)

                    if (grid[i + 1] > 0) {
                        let zero = (i + i + 3) / (2 * grid.length)
                        this.zeroLine(d['name'], zero)
                    }
                    this.diffGradient.append("stop")
                        .attrs({
                            "offset": 100 * x + "%",
                            "stop-color": this.$store.rankDiffColor.getColorByValue((val[i]))
                        })
                }
            }
        },

        clearZeroLine() {
            d3.selectAll('.zeroLine').remove()
            d3.selectAll('.zeroLineText').remove()
        },

        zeroLine(node, y1) {
            if (this.renderZeroLine[node] == undefined) {
                d3.select('#ensemble-callsite-' + this.nidNameMap[node])
                    .append('line')
                    .attrs((d) => {
                        return {
                            'class': 'zeroLine',
                            "x1": 0,
                            "y1": y1 * d.height,
                            "x2": this.nodeWidth,
                            "y2": y1 * d.height
                        }
                    })
                    .style('opacity', (d) => {
                        return 1
                    })
                    .style("stroke", '#000')
                    .style("stroke-width", (d) => {
                        return 5
                    })

                d3.select('#ensemble-callsite-' + this.nidNameMap[node])
                    .append('text')
                    .attrs({
                        'class': 'zeroLineText',
                        'dy': '0',
                        'x': this.nodeWidth / 2 - 10,
                        'y': (d) => y1 * d.height - 5
                    })
                    .style('opacity', 1)
                    .style('font-size', '20px')
                    .text((d) => {
                        return 0
                    })
                this.renderZeroLine[node] = true
            }
            else {
            }
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
                    return "url(#diff-gradient-" + d.client_idx + ")"
                })
        },

        //Gradients
        clearGradients() {
            this.svg.selectAll('.mean-gradient').remove()
        },

        clear() {
        },
    }
}