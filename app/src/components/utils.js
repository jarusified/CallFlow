/** 
 * Copyright 2017-2020 Lawrence Livermore National Security, LLC and other
 * CallFlow Project Developers. See the top-level LICENSE file for details.
 * 
 * SPDX-License-Identifier: MIT
 */

import * as d3 from "d3";


export function formatName(name) {
	if (name.length < 20) {
		return name;
	}
	let ret = this.trunc(name, 20);
	return ret;
}

export function formatRuntimeWithUnits(val) {
	if (val == 0) {
		return val;
	}
	let format = d3.format(".2");
	return format(val);
}

export function formatRunCounts(val) {
	if (val == 1) {
		return val + " run";
	}
	return val + " runs";
}

export function formatRuntimeWithoutUnits(val) {
	let format = d3.format(".2");
	return format(val);
}

// Returns [mantessa, exponent, max_exponent]
export function formatRuntimeWithExponent(val, min_exponent = 0) {
	let format = d3.format(".2");
	let ret = format(val);
	if (ret == 0) {
		return [0, 0, min_exponent];
	}

	let exponent = 0;
	let multiplier = 0;
	let mantessa = 0;
	if (ret.indexOf("e") != -1) {
		let split_ret_by_e = ret.toString().split("e");
		exponent = parseInt(split_ret_by_e[1].split("+")[1]);
		multiplier = parseInt(exponent) - min_exponent;
		mantessa = parseFloat(split_ret_by_e[0]); //* (10 ** multiplier));
	}
	return [mantessa.toFixed(2), exponent, min_exponent];
}

// Returns only the exponenet of the value. 
export function formatExponent(val) {
	let format = d3.format(".2");
	let ret = format(val);
	let exponent = ret;
	if (ret.indexOf("e") != -1) {
		exponent = parseInt(ret.toString().split("e")[1].split("+")[1]);
	}
	else {
		exponent = 0;
	}
	return exponent;
}

export function measureText(string, fontSize = 10) {
	const widths = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.2796875, 0.2765625, 0.3546875, 0.5546875, 0.5546875, 0.8890625, 0.665625, 0.190625, 0.3328125, 0.3328125, 0.3890625, 0.5828125, 0.2765625, 0.3328125, 0.2765625, 0.3015625, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.2765625, 0.2765625, 0.584375, 0.5828125, 0.584375, 0.5546875, 1.0140625, 0.665625, 0.665625, 0.721875, 0.721875, 0.665625, 0.609375, 0.7765625, 0.721875, 0.2765625, 0.5, 0.665625, 0.5546875, 0.8328125, 0.721875, 0.7765625, 0.665625, 0.7765625, 0.721875, 0.665625, 0.609375, 0.721875, 0.665625, 0.94375, 0.665625, 0.665625, 0.609375, 0.2765625, 0.3546875, 0.2765625, 0.4765625, 0.5546875, 0.3328125, 0.5546875, 0.5546875, 0.5, 0.5546875, 0.5546875, 0.2765625, 0.5546875, 0.5546875, 0.221875, 0.240625, 0.5, 0.221875, 0.8328125, 0.5546875, 0.5546875, 0.5546875, 0.5546875, 0.3328125, 0.5, 0.2765625, 0.5546875, 0.5, 0.721875, 0.5, 0.5, 0.5, 0.3546875, 0.259375, 0.353125, 0.5890625];
	const avg = 0.5279276315789471;
	return string
		.split("")
		.map(c => c.charCodeAt(0) < widths.length ? widths[c.charCodeAt(0)] : avg)
		.reduce((cur, acc) => acc + cur) * fontSize;
}

export function addIndexToBeginning(arr) {
	let ret = [];
	for (let i = 0; i < arr.length; i += 1) {
		ret.push(i + ". " + arr[i]);
	}
	return ret;
}

export function truncNames(str, len) {
	if (str.indexOf("=")) {
		str = str.split("=")[0];
	}

	if (str.indexOf(":") > -1) {
		let str_list = str.split(":");
		str = str_list[str_list.length - 1];
	}

	str = str.replace(/<unknown procedure>/g, "proc ");
	return (str.length > len) ? str.substr(0, len - 1) + "..." : str;
}

export function textSize(id, text) {
	const container = d3.select("#" + id)
		.append("svg");
	container.append("text")
		.attrs({
			x: -99999,
			y: -99999
		})
		.text((d) => text);
	const size = container.node().getBBox();
	container.remove();
	return {
		width: size.width,
		height: size.height
	};
}

export function getGradients(store, node) {
	let nodeName = "";
	let gradients = {};
	if (node.type == "super-node" && store.modules["ensemble"][node.module] != undefined) {
		nodeName = node.module;
		gradients = store.modules["ensemble"][nodeName][store.selectedMetric]["gradients"];
	}
	else if (node.type == "component-node") {
		nodeName = node.name;
		gradients = store.callsites["ensemble"][nodeName][store.selectedMetric]["gradients"];
	}
	else if (node.type == "intermediate") {
		gradients = {};
	}
	return gradients;
}

/**
 * Remove duplicates from an array.
 * @param {*} arr 
 */
export function removeDuplicates(arr) {
	var seen = {};
	return arr.filter(function (item) {
		return seen.hasOwnProperty(item) ? false : (seen[item] = true);
	});
}

// create a dummy element, apply the appropriate classes,
// and then measure the element
export function measure(text) {
	if (!text || text.length === 0) return { height: 0, width: 0 };

	const container = d3.select("body").append("svg").attr("class", "dummy");
	container.append("text").attrs({ x: -1000, y: -1000 }).text(text);

	const bbox = container.node().getBBox();
	container.remove();

	return { height: bbox.height, width: bbox.width };
}

/**
 * 
 * @param {*} text 
 * @param {*} width 
 */
export function textWrap(text, width) {
	text.each(function () {
		var text = d3.select(this),
			words = text.text().split(/\s+/).reverse(),
			word,
			line = [],
			lineNumber = 0,
			lineHeight = 1.1, // ems
			x = text.attr("x"),
			y = text.attr("y"),
			dy = 0,
			tspan = text.text(null).append("tspan").attr("dy", dy + "em");

		while ((word = words.pop())) {
			line.push(word);
			tspan.text(line.join(" "));
			if (tspan.node().getComputedTextLength() > width) {
				line.pop();
				tspan.text(line.join(" "));
				line = [word];
				tspan = text.append("tspan").attr("x", x).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
			}
		}
	});
}

/**
 * Calculate the distance between two given points.
 * @param {Number} x1 1st coordinate (x)
 * @param {Number} y1 1st coordinate (y)
 * @param {Number} x2 2nd coordinate (x)
 * @param {Number} y2 2nd coordinate (y)
 */
export function distanceBtwnPoints(x1, y1, x2, y2) {
	const a = x1 - x2;
	const b = y1 - y2;
	return Math.abs(Math.sqrt(a * a + b * b));
}

/**
 * Split string to lists by , (paranthesis proof)
 * @param {*} string 
 */
export function stringToList(string) {
	const re = /(:\s|,\s)/; // regular expression with capturing parentheses
	return string.split(re);
}