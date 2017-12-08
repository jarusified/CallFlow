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
// ////////////// file paths for the data///////////////
const fs = require('fs');
const express = require('express');
const LineByLineReader = require('line-by-line');
const argv = require('yargs').argv;

const app = express();

const CalcLM3 = require('./server/sankeyCalc.js');
const SankeySplitNode = require('./server/xmlParser.js');


const server = require('http').Server(app);

let nodeArray;
let sanKeyMetricDataLM;
let sankeyData;
let procIDArray = [];
let splitByParentList = [];
let entryExitDataNodeSplit;
let nodePaths;
let functionList;
let staticGraph; // this is the static graph we can load upond page refresh;
let staticFunctionList;
let filePath;
let xmlFile;
let portNumber;
let nodeMetricFile;
let nodeMetricReader;
let configFile;
let dataSetFile;
let dataSetInfo;
let xmlTree;
let procedureTable;
let resGlobal = null; // this is use to return the data to the browser

const nodeMetric = {};
const nodeIDKeep = []; // a array of node id got when read in the metric file

/* Unused variables */
// let date1;
// let date2;
// const splitParentList = {};
// let callMetrixData;
// let entryExitData;
// const clusterMetrix = {};
// const clusterList = {};
// const numberOfClusters = 16;
// const lmMatrix = {};
// let loadModuleTable;
/* const options = {
  mode: 'text',
  pythonPath: 'python3',
  scriptPath: './',
  pythonOptions: ['-u'],
  args: [numberOfClusters],
}; */
// let LMInternalCallPath;
// let sanKeyMetricData;
// let nodeInfo;
// let entry;
// let exit;
// let nodeRemove;

function exception(msg1, msg2) {
    console.log(msg1 + msg2);
}

function preCheck() {
    if (!argv.d) {
        exception('I do not know where to look for the data set');
    } else {
        dataSetFile = argv.d;
    }

    if (!fs.existsSync(dataSetFile)) {
        exception('Sorry no such dataset exist at', datasetFile);
    } else {
        dataSetInfo = require(dataSetFile);
    }

    if (dataSetInfo.path === null) {
        exception('I need the path information');
    } else {
        filePath = dataSetInfo.path;
    }

    if (dataSetInfo.experiment === null || !fs.existsSync(filePath + dataSetInfo.experiment)) {
        exception('No xml file found at', filePath + dataSetInfo.experiment);
    } else {
        xmlFile = filePath + dataSetInfo.experiment;
    }

    if (dataSetInfo.nodeMetric === null || !fs.existsSync(filePath + dataSetInfo.nodeMetric)) {
        exception('No metric file found at', filePath + dataSetInfo.nodeMetric);
    } else {
        nodeMetricFile = filePath + dataSetInfo.nodeMetric;
        nodeMetricReader = new LineByLineReader(nodeMetricFile);
    }
    if (dataSetInfo.config != null) {
        configFile = filePath + dataSetInfo.config;
    }
    if (dataSetInfo.port != null) {
        portNumber = parseInt(dataSetInfo.port, 10);
    }
}

preCheck();
const port = process.env.PORT || portNumber || 8500;
const host = process.env.HOST || 'localhost';
// host = process.env.HOST || "detoo.cs.ucdavis.edu";


app.use(express.static(`${__dirname}/public`));

/* Add a SumArray method to all arrays by expanding the
 Array prototype(do this once in a general place) */
Array.prototype.SumArray = function (arr) {
    const ret = [];
    if (arr != null && this.length === arr.length) {
        for (let i = 0; i < arr.length; i += 1) {
            ret.push(this[i] + arr[i]);
        }
    }

    return ret;
};

nodeMetricReader.on('line', (line) => {
    const myOBJ = JSON.parse(line);
    nodeIDKeep.push(parseInt(myOBJ.id), 10);
    nodeMetric[myOBJ.id] = myOBJ;
});

nodeMetricReader.on('end', () => {
    console.log('done with reading metric data, begin reading xml file');
    // var xmlFile = new fileLoader('../../data/miranda1/experiment.xml', myCallBack);
    date1 = new Date();
    const xml2 = new SankeySplitNode(xmlTree, xmlFile, sankeySplitNodeCallBack, configFile, [-99999], nodeMetric, [], nodeIDKeep);
});

function sankeySplitNodeCallBack(data) {
    console.log('done spliting node, begin calc edges');
    nodeArray = data.nodeArray;
    sanKeyMetricDataLM = data.sanKeyMetricDataLM;
    entryExitDataNodeSplit = data.entryExitData;
    nodePaths = data.nodePaths;
    procedureTable = data.procedureTable;

    // from the nodeSplitMiranda.js
    //  const finalTree = data.finalTree;
    //  const keepEdges = data.keepEdges;
    //  const nodeList = data.nodeList;
    //  let keepEdges = data.keepEdges;
    staticFunctionList = data.functionList;

    const connectionInfo = data.connectionInfo;

    //  const cTime1 = new Date();
    // var lmcalc = new calcLM3(nodeArray, nodeMetric, sanKeyMetricDataLM, nodePaths);
    const lmcalc = new CalcLM3(nodeArray, nodeMetric, sanKeyMetricDataLM, nodePaths, connectionInfo);

    // var lmcalc = new calcMiranda(finalTree, nodeList, nodePaths, nodeMetric, keepEdges);

    const result = lmcalc.compute();
    sankeyData = result.newSankey;
    // nodeRemove = result["nodeRemove"];

    date2 = new Date();

    //  const diff = date2 - date1;
    // console.log("the time it take to load and calc is, ", diff);
    // console.log('the time it take to calc the edges is', date2 - cTime1);

    let nodesDeepCopy = [];
    const edgesDeepCopy = [];
    let nodeListDeepCopy = {};
    let edgeListDeepCopy = {};
    sankeyData.edges.forEach((edge) => {
        const tempObj = JSON.parse(JSON.stringify(edge));
        edgesDeepCopy.push(tempObj);
    });
    nodesDeepCopy = JSON.parse(JSON.stringify(sankeyData.nodes));
    nodeListDeepCopy = JSON.parse(JSON.stringify(sankeyData.nodeList));
    edgeListDeepCopy = JSON.parse(JSON.stringify(sankeyData.edgeList));

    staticGraph = {
        nodes: nodesDeepCopy,
        edges: edgesDeepCopy,
        nodeList: nodeListDeepCopy,
        edgeList: edgeListDeepCopy,
    };

    server.listen(port, host, () => {
        console.log('Sever started, listening', host, port);
    });
}

app.get('/', (req, res) => {
    splitByParentList = [];
    procIDArray = [];
    functionList = staticFunctionList;

    res.sendFile(`${__dirname}/index.html`);
});

app.get('/dataSetInfo', (req, res) => {
    res.json(dataSetInfo);
});

app.get('/data', (req, res) => {
    // runPython(res);
});

app.get('/getNodeMetrics', (req, res) => {
    res.json(nodeMetric);
});

app.get('/procedureTable', (req, res) => {
    res.json(procedureTable);
});

app.get('/getSankey', (req, res) => {
    // var lmID = parseInt(req.query["lmID"]);
    // resGlobal = res;
    // getSankey(lmID);

    // console.log("getting the sankey data");
    // res.json(sankeyData);

    // var temp = {"nodes" : staticGraph["nodes"], "edges" : staticGraph["edges"]};
    // fs.writeFileSync("nodeEdgeTest.json", JSON.stringify(temp));
    procIDArray = [];
    splitByParentList = [];
    sankeyData = staticGraph;
    const hisData = computeHistogram();
    const resData = {
        graph: staticGraph,
        histogramData: hisData,
    };
    res.json(resData);
});

app.get('/splitNode', (req, res) => {
    // var level = parseInt( req.query["nodeLevel"] )
    // var specialID = req.query["specialID"];
    // var highestProc = calcHighestProcs(level, specialID);

    // var myID = parseInt(highestProc["procID"])

    const idList = req.query.idList;

    idList.forEach((sID) => {
        const myID = parseInt(sID, 10);
        if (procIDArray.indexOf(myID) === -1 || procIDArray.length === 0) {
            procIDArray.push(myID);
        }
    });

    resGlobal = res;

    // var xml2 = new sankeySplitNode('../../data/miranda1/experiment.xml', splitNodeCallBack, procIDArray);
    const xml2 = new SankeySplitNode(xmlTree, xmlFile, splitNodeCallBack2, configFile, procIDArray, nodeMetric, splitByParentList, nodeIDKeep);
});

app.get('/getList', (req, res) => {
    const level = parseInt(req.query.nodeLevel, 10);
    const specialID = req.query.specialID;

    const tempList = [];
    entryExitDataNodeSplit[specialID].enter.forEach((entryDat) => {
        const name = procedureTable[entryDat];
        const tempObj = {
            name,
            procID: entryDat,
        };
        tempList.push(tempObj);
    });
    res.json(tempList);
});

// this get the functions of more than one lms
app.get('/getLists', (req, res) => {
    const specialID = req.query.specialID;
    if (functionList[specialID] != null) {
        const functionListResult = {};
        const functionListObject = functionList[specialID];
        const functionListObjectKeys = Object.keys(functionListObject);
        functionListObjectKeys.forEach((procedureID) => {
            if (functionListResult[procedureID] === null) {
                functionListResult[procedureID] = {
                    procID: procedureID,
                    name: procedureTable[procedureID],
                    value: 0,
                    excVal: 0,
                };
            }

            const nodeIDList = functionList[specialID][procedureID];
            nodeIDList.forEach((nodeID) => {
                const incTime = nodeMetric[nodeID].inc;
                let temp = 0;
                incTime.forEach((val, idx) => {
                    temp += val;
                });

                const excTime = nodeMetric[nodeID].exc;
                let excTemp = 0;
                excTime.forEach((val, idx) => {
                    excTemp += val;
                });

                functionListResult[procedureID].value += temp / Math.max(incTime.length, 1);

                functionListResult[procedureID].excVal += excTemp / Math.max(excTime.length, 1);
            });
        });

        res.json(functionListResult);
    } else {
    // console.log("Cannot find function list for", specialID);
        res.json({});
    }
});

app.get('/getRuntimeOfNode', (req, res) => {
    const idOfNode = parseInt(req.query.nodeID, 10);
    const levelOfNode = parseInt(req.query.nodeLevel, 10);

    // if(req.query["name"] === "root"){
    // 	lmIDofNode = "root";
    // }
    // else{
    const lmIDofNode = parseInt(req.query.lmID, 10);
    // }
    const procIDofNode = req.query.specialID;

    // var nodeOfInterest = sanKeyMetricData[lmIDofNode][levelOfNode][procIDofNode];
    const nodeOfInterest = sanKeyMetricDataLM[levelOfNode][procIDofNode];
    const nodeIDs = [];
    let sumsInc = [];
    let sumsExc = [];
    nodeOfInterest.forEach((node, idx) => {
        nodeIDs.push(node.nodeID);
    });

    nodeIDs.forEach((id, idx) => {
    // grab runtime for this id
        const runTimes = nodeMetric[id];
        if (idx === 0) {
            sumsInc = runTimes.inc;
            sumsExc = runTimes.exc;
        } else {
            sumsInc = sumsInc.SumArray(runTimes.inc);
            sumsExc = sumsExc.SumArray(runTimes.exc);
        }
    });

    res.json({
        inc: sumsInc,
        exc: sumsExc,
    });
});

app.get('/splitNodeByParents', (req, res) => {
    // splitParentList
    const parentProcList = req.query.parentProcList;
    const nodeLabel = req.query.nodeLabel;
    const specIDofSplitNode = req.query.nodeSpecialID;

    if (splitByParentList.indexOf(specIDofSplitNode) === -1) {
        splitByParentList.push(specIDofSplitNode);
    }

    resGlobal = res;

    const xml2 = new sankeySplitNode(xmlTree, xmlFile, splitNodeCallBack2, configFile, procIDArray, nodeMetric, splitByParentList, nodeIDKeep);
});

app.get('/getHistogramScatterData', (req, res) => {
    const sankeyID = req.query.sankeyID;
    const specialID = req.query.specialID;
    const node = sankeyData.nodes[specialID];
    const uniqueNodeIDList = node.uniqueNodeID;
    let tempInc = [];
    let tempExc = [];
    uniqueNodeIDList.forEach((nodeID, idx) => {
        const incRuntime = nodeMetric[parseInt(nodeID)].inc;
        const excRuntime = nodeMetric[parseInt(nodeID)].exc;
        if (idx === 0) {
            tempInc = incRuntime;
            tempExc = excRuntime;
        } else {
            tempInc = tempInc.SumArray(incRuntime);
            tempExc = tempExc.SumArray(excRuntime);
        }
    });
    res.json({
        inc: tempInc,
        exc: tempExc,
    });
});

app.get('/calcEdgeValues', (req, res) => {
    // this could be a problem when there are lots of edges
    const edgeSet1 = [];
    const edgeSet2 = [];
    const tempEdges = sankeyData.edges.slice();

    const processID = req.query.processIDList;
    const processIDList = [];
    processID.forEach((pID) => {
        processIDList.push(parseInt(pID), 10);
    });
    tempEdges.forEach((edge) => {
        const idList = edge.nodeIDList;
        let edgeValueForBrush = 0;
        let edgeValueForNonBrush = 0;
        idList.forEach((id) => {
            const runTime = nodeMetric[id].inc;
            let numberOfIDInBrush = 0;
            let numberOfIDnotBrush = 0;
            let tempValBrush = 0;
            let tempValNonBrush = 0;
            runTime.forEach((val, idx) => {
                if (processIDList.indexOf(idx) > -1) {
                    // edgeValueForBrush += val;
                    numberOfIDInBrush += 1;
                    tempValBrush += val;
                } else {
                    // edgeValueForNonBrush += val;
                    numberOfIDnotBrush += 1;
                    tempValNonBrush += val;
                }
            });
            edgeValueForBrush += tempValBrush / Math.max(numberOfIDInBrush, 1);
            edgeValueForNonBrush += tempValNonBrush / Math.max(numberOfIDnotBrush, 1);
        });
        const tempE1 = JSON.parse(JSON.stringify(edge));
        tempE1.value = edgeValueForBrush;
        edgeSet1.push(tempE1);

        const tempE2 = JSON.parse(JSON.stringify(edge));
        tempE2.value = edgeValueForNonBrush;
        edgeSet2.push(tempE2);
    });
    res.json({
        brush: edgeSet1,
        nonBrush: edgeSet2,
    });
});

function splitNodeCallBack(data) {
    nodeArray = data.nodeArray;
    sanKeyMetricDataLM = data.sanKeyMetricDataLM;

    const lmcalc = new calcLM3(nodeArray, nodeMetric, sanKeyMetricDataLM);
    const result = lmcalc.compute();
    sankeyData = result.newSankey;
    nodeRemove = result.nodeRemove;

    console.log('done with split node');
    resGlobal.json(sankeyData);
}

function splitNodeCallBack2(data) {
    nodeArray = data.nodeArray;
    sanKeyMetricDataLM = data.sanKeyMetricDataLM;
    entryExitDataNodeSplit = data.entryExitData;
    nodePaths = data.nodePaths;
    procedureTable = data.procedureTable;

    // from the nodeSplitMiranda.js
    const finalTree = data.finalTree;
    var keepEdges = data.keepEdges;
    const nodeList = data.nodeList;
    var keepEdges = data.keepEdges;
    functionList = data.functionList;

    const connectionInfo = data.connectionInfo;
    const cTime1 = new Date();
    // var lmcalc = new calcLM3(nodeArray, nodeMetric, sanKeyMetricDataLM, nodePaths)
    const lmcalc = new calcLM3(nodeArray, nodeMetric, sanKeyMetricDataLM, nodePaths, connectionInfo);
    // var lmcalc = new calcMiranda(finalTree, nodeList, nodePaths, nodeMetric, keepEdges);
    const result = lmcalc.compute();
    sankeyData = result.newSankey;
    console.log('done with split node');
    // var temp = {"nodes" : sankeyData["nodes"], "edges" : sankeyData["edges"]};
    // fs.writeFileSync("nodeEdgeTest2.json", JSON.stringify(temp));
    const hisData = computeHistogram();
    const resData = {
        graph: sankeyData,
        histogramData: hisData,
    };
    // resGlobal.json(sankeyData);
    resGlobal.json(resData);
}

// this function compute a mini histogram for each speical ID
function computeHistogram() {
    const sankeyNodes = sankeyData.nodes;
    const histogramData = {};
    const numbOfBins = 20;
    let maxFreq = 0;
    let globalXvals;

    const specialIDs = Object.keys(sankeyNodes);
    specialIDs.forEach((specialID) => {
        const sankNode = sankeyNodes[specialID];
        const uniqueNodeIDList = sankNode.uniqueNodeID;
        let tempInc = [];
        // calculate runtime for this sank node
        uniqueNodeIDList.forEach((nodeID, idx) => {
            const incRuntime = nodeMetric[parseInt(nodeID)].inc;
            if (idx === 0) {
                tempInc = incRuntime;
            } else {
                tempInc = tempInc.SumArray(incRuntime);
            }
        });
        // This section will bin the data////

        const dataSorted = tempInc.slice();
        dataSorted.sort((a, b) => a - b);

        // compute the average of this sankey node
        let average = 0;
        let sumVal = 0;
        dataSorted.forEach((val) => {
            sumVal += val;
        });

        average = sumVal / dataSorted.length;

        const dataMin = dataSorted[0];
        const dataMax = dataSorted[dataSorted.length - 1];
        // console.log('the max-min/avg is',  (dataMax - dataMin) / average );
        sankeyNodes[specialID].nRange = (dataMax - dataMin) / average;
        const dataWidth = ((dataMax - dataMin) / numbOfBins);
        const freq = [];
        const binContainsProcID = {};
        const xVals = [];
        for (let i = 0; i < numbOfBins; i++) {
            xVals.push(i);
            freq.push(0);
        }

        tempInc.forEach((val, idx) => {
            let pos = Math.floor((val - dataMin) / dataWidth);
            if (pos >= numbOfBins) {
                pos = numbOfBins - 1;
            }
            freq[pos] += 1;
            maxFreq = Math.max(maxFreq, freq[pos]);
        });
        histogramData[specialID] = {
            numbOfBins,
            freq,
            xVals,
        };
        globalXvals = xVals;
    });
    return {
        histogramData,
        maxFreq,
        globalXvals,
    };
}