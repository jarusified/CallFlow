import tpl from '../../../html/ensembleSupergraph/node.html'
import * as d3 from 'd3'
import * as utils from '../../utils'

export default {
    template: tpl,
    name: 'TargetLine',
    components: {},

    data: () => ({
        id: 'target-line'
    }),

    methods: {
        init(nodes, svg) {
            this.nodes = nodes
            this.svg = svg

            this.ensemble_module_data = this.$store.modules['ensemble']
            this.ensemble_callsite_data = this.$store.callsites['ensemble']

            this.visualize()
        },

        renderTargetLine(data, node_data, node_name) {
            let gradients = data['ensemble'][node_name][this.$store.selectedMetric]['gradients']

            let targetPos = gradients['dataset']['position'][this.$store.selectedTargetDataset] + 1
            let binWidth = node_data.height / (this.$store.selectedRunBinCount)

            let y = 0
            if (node_name == 'LeapFrog') {
                y = binWidth * targetPos - binWidth / 2 - 10
            }
            else {
                y = binWidth * targetPos - binWidth / 2
            }

            d3.select('#ensemble-callsite-' + node_data.client_idx)
                .append('line')
                .attrs({
                    "class": 'targetLines',
                    "id": 'line-2-' + this.$store.selectedTargetDataset + '-' + node_data['client_idx'],
                    "x1": 0,
                    "y1": y,
                    "x2": this.nodeWidth,
                    "y2": y,
                    "stroke-width": 5,
                    "stroke": this.$store.color.target
                })
        },

        drawTargetLine() {
            let targetDataset = this.$store.selectedTargetDataset
            let data = {}
            let node_name = ''

            for (let i = 0; i < this.graph.nodes.length; i++) {
                let node_data = this.graph.nodes[i]
                if (this.graph.nodes[i].type == 'super-node' && this.$store.modules[targetDataset][node_data["module"]] != undefined) {
                    node_name = this.graph.nodes[i].module
                    data = this.$store.modules
                    this.renderTargetLine(data, node_data, node_name)
                }
                else if (this.graph.nodes[i].type == 'component-node' && this.$store.callsites[targetDataset][node_data["name"]] != undefined) {
                    node_name = this.graph.nodes[i].name
                    data = this.$store.callsites
                    this.renderTargetLine(data, node_data, node_name)
                }
                else {
                    continue
                }
            }
        },



        visualize() {

        },



        clear() {
        },
    }
}