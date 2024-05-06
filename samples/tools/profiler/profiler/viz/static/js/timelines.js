function drawTimeline(svg, data) {
    const width = svg.node().parentNode.clientWidth;
    const height = svg.node().parentNode.clientHeight;

    console.log("Width: ", width);
    console.log("Height: ", height);

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const margin = { top: 10, right: 50, bottom: 40, left: 100 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    const sources = Array.from(new Set(data.map(d => d.message.source)));
    const sourceCount = sources.length;

    const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
        .domain([0, data.length])
        .range([0, chartWidth]);

    const y = d3.scaleBand()
        .domain(sources)
        .range([0, chartHeight])
        .padding(0.1);

    const color = d3.scaleOrdinal(d3.schemeCategory10)
        .domain(sources);

    const xAxis = d3.axisBottom(x)
        .ticks(Math.min(data.length, 10))
        .tickFormat(d => `${d + 1}`);

    const yAxis = d3.axisLeft(y);

    // Draw the timelines
    sources.forEach(source => {
        const sourceMessages = data.filter(d => d.message.source === source);

        g.selectAll(`.bar-${source}`)
            .data(sourceMessages)
            .enter()
            .append("rect")
            .attr("class", `bar-${source}`)
            .attr("x", d => x(data.indexOf(d)))
            .attr("y", y(source))
            .attr("width", x(1) - x(0))
            .attr("height", y.bandwidth())
            .attr("fill", color(source))
            .on("click", function (event, d) {
                const messageClickedEvent = new CustomEvent("messageClicked", {
                    bubbles: true,
                    detail: {
                        message: d.message
                    }
                });
                window.dispatchEvent(messageClickedEvent);
            });
    });

    // Add x-axis
    g.append("g")
        .attr("class", "x-axis")
        .attr("transform", `translate(0,${chartHeight})`)
        .call(xAxis)
        .append("text")
        .attr("class", "x-axis-label")
        .attr("x", chartWidth / 2)
        .attr("y", margin.bottom - 5)
        .attr("fill", "black")
        .attr("text-anchor", "middle")
        .text("Message Index");

    // Add y-axis
    g.append("g")
        .attr("class", "y-axis")
        .call(yAxis)
        .append("text")
        .attr("class", "y-axis-label")
        .attr("x", -margin.left + 10)
        .attr("y", chartHeight / 2)
        .attr("fill", "black")
        .attr("text-anchor", "middle")
        .attr("transform", `rotate(-90, -${margin.left - 10}, ${chartHeight / 2})`)
        .text("Source");
}


export class TimelineWidget {
    constructor({ id, profileArray }) {
        this.id = id;
        this.profileArray = profileArray;
    }

    compose() {
        // Create a new div element
        const div = document.createElement('div');
        div.id = this.id;
        div.className = "timeline-widget";

        // Add a heading to the div element
        const heading = document.createElement('h3');
        heading.textContent = "Message Timeline";
        div.appendChild(heading);

        // Create an SVG element inside the div
        const svg = d3.select(div).append("svg")
            .attr("width", "90%")
            .attr("height", "90%");

        // Call the drawBarChart function to render the bar chart
        window.setTimeout(() => drawTimeline(svg, this.profileArray), 0);

        // drawTimeline(svg, this.profileArray);

        // Append the SVG element to the div
        return div;
    }
}
