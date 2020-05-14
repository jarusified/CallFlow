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


        visualize() {

        },

        drawGuides(node_data, type) {
            let modules_data = this.$store.modules
            let callsite_data = this.$store.callsites

            let node_name = ''
            let gradients = {}
            if (node_data.type == 'super-node') {
                node_name = node_data.module
                gradients = modules_data['ensemble'][node_name][this.$store.selectedMetric]['gradients']
            }
            else if (node_data.type == 'component-node') {
                node_name = node_data.name
                gradients = callsite_data['ensemble'][node_name][this.$store.selectedMetric]['gradients']
            }
            else {
                gradients = {}
            }

            let histogram = gradients['hist']
            let datasetPositionMap = gradients['dataset']['position']

            let grid = histogram.x
            let vals = histogram.y

            let targetPos = 0
            let binWidth = node_data.height / (grid.length)

            let positionDatasetMap = {}
            // Create a position -> dataset map
            for (let dataset in datasetPositionMap) {
                let datasetPosition = datasetPositionMap[dataset]
                if (positionDatasetMap[datasetPosition] == undefined) {
                    positionDatasetMap[datasetPosition] = []
                }
                positionDatasetMap[datasetPosition].push(dataset)
            }

            this.guidesG = d3.select('#ensemble-callsite-' + node_data.client_idx)
                .append('g')

            for (let idx = 0; idx < grid.length; idx += 1) {
                let y = binWidth * (idx)

                d3.selectAll('.ensemble-edge')
                    .style('opacity', 0.5)

                // For drawing the guide lines that have the value.
                this.guidesG
                    .append('line')
                    .attrs({
                        "class": 'gradientGuides-' + type,
                        "id": 'line-2-' + node_data['client_idx'],
                        "x1": 0,
                        "y1": y,
                        "x2": this.nodeWidth,
                        "y2": y,
                        "stroke-width": 1.5,
                        'opacity': 0.3,
                        "stroke": '#202020'
                    })

                let fontSize = 12
                if (vals[idx] != 0) {
                    // For placing the run count values.
                    // for (let i = 0; i < positionDatasetMap[idx].length; i += 1) {
                    let textGuideType = 'summary'
                    let leftSideText = ''
                    if (textGuideType == 'detailed') {
                        let text = positionDatasetMap[idx][0]
                        if (positionDatasetMap[idx].length < 3) {
                            for (let i = 0; i < 3; i += 1) {
                                leftSideText = positionDatasetMap[idx][i]
                                this.guidesG
                                    .append('text')
                                    .attrs({
                                        "class": 'gradientGuidesText-' + type,
                                        "id": 'line-2-' + node_data['client_idx'],
                                        "x": -60,
                                        "y": y + fontSize / 2 + binWidth / 2 + fontSize * i,
                                        'fill': 'black'
                                    })
                                    .style('z-index', 100)
                                    .style('font-size', fontSize + 'px')
                                    .text(leftSideText)

                            }
                        }
                        else {
                            let count = positionDatasetMap[idx].length - 3
                            text = text + '+' + count

                            this.guidesG
                                .append('text')
                                .attrs({
                                    "class": 'gradientGuidesText-' + type,
                                    "id": 'line-2-' + node_data['client_idx'],
                                    "x": -60,
                                    "y": y + fontSize / 2 + binWidth / 2 + fontSize * i,
                                    'fill': 'black'
                                })
                                .style('z-index', 100)
                                .style('font-size', fontSize + 'px')
                                .text(leftSideText)
                        }

                    }
                    else if (textGuideType == 'summary') {
                        leftSideText = utils.formatRunCounts(vals[idx])
                        this.guidesG
                            .append('text')
                            .attrs({
                                "class": 'gradientGuidesText-' + type,
                                "id": 'line-2-' + node_data['client_idx'],
                                "x": -60,
                                "y": y + fontSize / 2 + binWidth / 2, //+ fontSize * i,
                                'fill': 'black'
                            })
                            .style('z-index', 100)
                            .style('font-size', fontSize + 'px')
                            .text(leftSideText)
                    }

                    // For placing the runtime values.
                    if (idx != 0 && idx != grid.length - 1) {
                        let text = utils.formatRuntimeWithUnits(grid[idx]) //+ this.formatRunCounts(vals[idx])
                        this.guidesG
                            .append('text')
                            .attrs({
                                "class": 'gradientGuidesText-' + type,
                                "id": 'line-2-' + node_data['client_idx'],
                                "x": this.nodeWidth + 10,
                                "y": y + fontSize / 2,
                                'fill': 'black'
                            })
                            .style('z-index', 100)
                            .style('font-size', fontSize + 'px')
                            .text(text)
                    }
                }

                if (idx == 0) {
                    this.guidesG
                        .append('text')
                        .attrs({
                            "class": 'gradientGuidesText-' + type,
                            "id": 'line-2-' + node_data['client_idx'],
                            "x": this.nodeWidth + 10,
                            "y": y,
                            'fill': 'black'
                        })
                        .style('z-index', 100)
                        .style('font-size', fontSize + 'px')
                        .text('Min. = ' + utils.formatRuntimeWithUnits(grid[idx]))
                }
                else if (idx == grid.length - 1) {
                    this.guidesG
                        .append('text')
                        .attrs({
                            "class": 'gradientGuidesText-' + type,
                            "id": 'line-2-' + node_data['client_idx'],
                            "x": this.nodeWidth + 10,
                            "y": y + 2 * binWidth,
                            'fill': 'black'
                        })
                        .style('z-index', 100)
                        .style('font-size', fontSize + 'px')
                        .text('Max. = ' + utils.formatRuntimeWithUnits(grid[idx]))
                }
            }
        },


        clear() {
            d3.selectAll('.gradientGuides-' + type).remove()
            d3.selectAll('.gradientGuidesText-' + type).remove()
        },
    }
}


