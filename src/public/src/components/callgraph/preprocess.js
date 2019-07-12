/** *****************************************************************************
 * Copyright (c) 2017, Lawrence Livermore National Security, LLC.
 * Produced at the Lawrence Livermore National Laboratory.
 *
 * Written by Suraj Kesavan <spkesavan@ucdavis.edu>.
 *
 * LLNL-CODE-740862. All rights reserved.
 *
 * This file is part of CallFlow. For details, see:
 * https://github.com/LLNL/CallFlow
 * Please also read the LICENSE file for the MIT License notice.
 ***************************************************************************** */

export default function preprocess(graph, refresh) {
    // graph = cleanGraph(graph);
    // graph = addUncertainityInfo(graph)
    graph = addMaxLevel(graph)
    graph = addLinkID(graph);
    graph = calculateFlow(graph);
    console.log("Graph after preprocessing: ", graph)
    return graph;
}

function cleanGraph(graph) {
    const new_nodes = [];
    let new_links = [];
    for (const node of graph.nodes) {
        if (node != undefined && node.name[0][node.name[0].length - 1] != '_') {
            new_nodes.push(node);
        }
    }

    for (const link of graph.links) {
        if (link.name != 'intermediate' || link.name != 'intermediate' || link.name != undefined) {
            new_links.push(link);
        }
    }

    // Remove the unnecessary edges
    const tempLinks = [];
    new_links.forEach((link) => {
        if ((link.source) != undefined && link.target != undefined) {
            tempLinks.push(link);
        }
    });
    new_links = tempLinks;

    return {
        nodes: new_nodes,
        links: new_links,
    };

}

function addUncertainityInfo(graph) {
    let dataset1 = {
        'libmonitor.so.0.0.0': [0.0, 0.0, 0.0, 194787687.0],
        'kripke': [0.0, 0.0, 472050.25, 194787687.0],
        'ld-2.17.so': [0.0, 0.0, 0.0, 5990.0],
        'libc-2.17.so': [0.0, 0.0, 0.0, 2413077.0],
        'libfabric.so.1.9.14': [0.0, 0.0, 0.0, 525976.0],
        'libm-2.17.so': [0.0, 0.0, 0.0, 5988.0],
        'libpsm2.so.2.1': [0.0, 0.0, 0.0, 245065.0],
        'libstdc++.so.6.0.20': [0.0, 0.0, 0.0, 604003.0],
        'libmpi.so.12.0.0': [0.0, 0.0, 5983.0, 2912673.0],
        '<unknown load module>': [5979.0, 11959.5, 11988.25, 41951.0]
    }
    let dataset2 = {
        'libmonitor.so.0.0.0': [0.0, 0.0, 5978.25, 194787687.0],
        'kripke': [0.0, 0.0, 5965.25, 194787687.0],
        'ld-2.17.so': [0.0, 5990.0, 23922.5, 107417.0],
        'libc-2.17.so': [0.0, 0.0, 0.0, 80080390.0],
        'libm-2.17.so': [0.0, 0.0, 0.0, 5980.0],
        'libpsm2.so.2.1': [0.0, 0.0, 0.0, 5773527.0],
        'libpthread-2.17.so': [0.0, 0.0, 5935.25, 17972.0],
        'libstdc++.so.6.0.20': [0.0, 0.0, 0.0, 80080390.0],
        'libintlc.so.5': [0.0, 0.0, 0.0, 5993.0],
        'libmpi.so.12.0.5': [0.0, 0.0, 0.0, 747178.0],
        '<unknown load module>': [5979.0, 11959.5, 11988.25, 41951.0]
    }

    for (const node of graph.nodes) {
        node.nrange = []
        if (node.name in dataset1) {
            let vals = dataset1[node.name]
            for (let i = 0; i < vals.length; i += 1) {
                node.nrange.push(vals[i])
            }
        }
        if (node.name in dataset2) {
            let vals = dataset2[node.name]
            for (let i = 0; i < vals.length; i += 1) {
                node.nrange.push(vals[i])
            }
        }
    }
    return graph
}


function addMaxLevel(graph) {
    let ret = 0
    let nodes = graph.nodes
    for (let i = 0; i < nodes.length; i += 1) {
        let node = nodes[i]
        if (ret < node.level) {
            ret = node.level
        }
    }
    graph['maxLevel'] = ret 
    return graph
}

/* Link: {
   sourceID : int, targetID: int , target: str, source: str
   } */
function addLinkID_(graph) {
    const nodeMap = {};
    for (const [idx, node] of graph.nodes.entries()) {
        nodeMap[node.name[0]] = idx;
    }


    const links = graph.links;
    for (const link of graph.links) {
        link['sourceID'] = nodeMap[link.source];
        link['targetID'] = nodeMap[link.target];
    }
    return graph;
}

/* Link: {
   sourceID : int, targetID: int , target: str, source: str
   } */
function addLinkID(graph) {
    const nodeMap = {};
    for (const [idx, node] of graph.nodes.entries()) {
        nodeMap[node.name] = idx;
    }

    const links = graph.links;
    for (const link of graph.links) {
        if (link.source == undefined || link.target == undefined) {
            continue;
        }

        if (link.source[link.source.length - 1] == '_' || link.target[link.target.length - 1] == '_') {
            continue;
        }
        link['sourceID'] = nodeMap[link.source];
        link['targetID'] = nodeMap[link.target];
    }
    return graph;
}

function calculateFlow(graph) {
    const nodes = graph.nodes;
    const links = graph.links;
    const outGoing = [];
    const inComing = [];
    nodes.forEach((node) => {
        const nodeLabel = node.name[0];

        links.forEach((link) => {
            if (nodes[link.sourceID] != undefined) {
                const linkLabel = nodes[link.sourceID].name;
                if (linkLabel == nodeLabel) {
                    if (outGoing[linkLabel] == undefined) {
                        outGoing[linkLabel] = 0;
                    }
                    outGoing[linkLabel] += link.weight;
                }
            }

        });

        links.forEach((link) => {
            if (nodes[link.targetID] != undefined) {
                const linkLabel = nodes[link.targetID].name;
                if (linkLabel == nodeLabel) {
                    if (inComing[linkLabel] == undefined) {
                        inComing[linkLabel] = 0;
                    }
                    inComing[linkLabel] += link.weight;
                }
            }

        });

        if (outGoing[nodeLabel] == undefined) {
            outGoing[nodeLabel] = 0;
        }

        if (inComing[nodeLabel] == undefined) {
            inComing[nodeLabel] = 0;
        }

        node.out = outGoing[nodeLabel];
        node.in = inComing[nodeLabel];

        node.inclusive = Math.max(inComing[nodeLabel], outGoing[nodeLabel]);
        node.exclusive = Math.max(inComing[nodeLabel], outGoing[nodeLabel]) - outGoing[nodeLabel];
    });

    return graph;
}