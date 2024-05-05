function setEqual(setA, setB) {
    if (setA.size !== setB.size) return false;
    for (const item of setA) if (!setB.has(item)) return false;
    return true;
}

function prepareGraphDataWithFrequency(messages) {
    const stateSets = [];
    const nodes = [];
    const linksMap = new Map();

    messages.forEach((msg, index) => {
        const stateSet = new Set(msg.states);

        let sourceIndex = stateSets.findIndex(s => setEqual(s, stateSet));
        if (sourceIndex === -1) {
            sourceIndex = stateSets.length;
            stateSets.push(stateSet);
            nodes.push({ id: sourceIndex, label: [...stateSet].join(', ') });
        }

        if (index < messages.length - 1) {
            const nextStateSet = new Set(messages[index + 1].states);
            let targetIndex = stateSets.findIndex(s => setEqual(s, nextStateSet));
            if (targetIndex === -1) {
                targetIndex = stateSets.length;
                stateSets.push(nextStateSet);
                nodes.push({ id: targetIndex, label: [...nextStateSet].join(', ') });
            }

            const key = `${sourceIndex}-${targetIndex}`;
            if (linksMap.has(key)) {
                linksMap.get(key).frequency += 1;
            } else {
                linksMap.set(key, { source: sourceIndex, target: targetIndex, frequency: 1 });
            }
        }
    });

    return { nodes, links: Array.from(linksMap.values()) };
}

function drawDirectedGraph(svg, graphData, width, height) {
    const { nodes, links } = graphData;

    svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 9)
        .attr("refY", 0)
        .attr("orient", "auto")
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "gray");

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).distance(100).strength(0.5).id(d => d.id))
        .force("charge", d3.forceManyBody().strength(-400))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("path")
        .data(links)
        .enter().append("path")
        .attr("stroke-width", 2)
        .attr("stroke", "gray")
        .attr("fill", "none")
        .attr("marker-end", "url(#arrowhead)");

    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(nodes)
        .enter().append("circle")
        .attr("r", 20)
        .attr("fill", "steelblue")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    const text = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(nodes)
        .enter().append("text")
        .attr("dy", 4)
        .attr("dx", -18)
        .text(d => d.label);

    const linkLabels = svg.append("g")
        .attr("class", "link-labels")
        .selectAll("text")
        .data(links)
        .enter().append("text")
        .attr("class", "link-label")
        .attr("fill", "black")
        .attr("font-size", "12px")
        .text(d => d.frequency);

    simulation.on("tick", () => {
        link.attr("d", d => {
            const radius = 20; // The radius of the node circles
            const curve = 0.5; // Adjust this for curvature

            if (d.source === d.target) {
                // Self-loop path
                const xOffset = 15;
                const loopRadius = 25; // Adjust to position the loop properly
                return `M${d.source.x},${d.source.y}
                        a${loopRadius},${loopRadius} 0 1,1
                        ${xOffset},${loopRadius}`;
            } else {
                // Calculate the angle and adjust the path
                const dx = d.target.x - d.source.x;
                const dy = d.target.y - d.source.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                const sourceX = d.source.x + (dx * radius) / distance;
                const sourceY = d.source.y + (dy * radius) / distance;
                const targetX = d.target.x - (dx * radius) / distance;
                const targetY = d.target.y - (dy * radius) / distance;

                const midX = (sourceX + targetX) / 2 + curve * dy;
                const midY = (sourceY + targetY) / 2 - curve * dx;

                return `M${sourceX},${sourceY}Q${midX},${midY} ${targetX},${targetY}`;
            }
        });

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        text
            .attr("x", d => d.x)
            .attr("y", d => d.y);

        linkLabels
            .attr("x", d => {
                if (d.source === d.target) {
                    // Self-loop label
                    return d.source.x + 10;
                } else {
                    // Calculate the midpoint for normal edges
                    const dx = d.target.x - d.source.x;
                    const dy = d.target.y - d.source.y;
                    const midX = (d.source.x + d.target.x) / 2 + 0.5 * dy; // Slight horizontal offset for positioning
                    return midX;
                }
            })
            .attr("y", d => {
                if (d.source === d.target) {
                    // Self-loop label
                    return d.source.y - 20;
                } else {
                    // Calculate the midpoint for normal edges
                    const dx = d.target.x - d.source.x;
                    const dy = d.target.y - d.source.y;
                    const midY = (d.source.y + d.target.y) / 2 - 0.5 * dx; // Above the curve
                    return midY;
                }
            });
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

export class DirectedGraphWidget {
    constructor({ id, messages, width = 400, height = 300 }) {
        this.id = id;
        this.messages = messages;
        this.width = width;
        this.height = height;
    }

    compose() {
        const div = document.createElement('div');
        div.id = this.id;
        div.className = "directed-graph-widget";

        // Add a heading
        const heading = document.createElement('h3');
        heading.textContent = "State Transition Graph";
        div.appendChild(heading);

        const svg = d3.select(div).append("svg")
            .attr("width", this.width)
            .attr("height", this.height);

        const graphData = prepareGraphDataWithFrequency(this.messages);
        drawDirectedGraph(svg, graphData, this.width, this.height);

        return div;
    }
}
