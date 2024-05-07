function drawBarChart(svg, data) {
    const width = svg.node().parentNode.clientWidth;
    const height = svg.node().parentNode.clientHeight;

    // Increase the left margin to accommodate long y-axis labels
    const margin = { top: 20, right: 30, bottom: 50, left: 100 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
        .domain([0, Math.ceil(d3.max(data, d => d.count))])
        .range([0, chartWidth]);

    const y = d3.scaleBand()
        .domain(data.map(d => d.label))
        .range([0, chartHeight])
        .padding(0.1);

    const xAxis = d3.axisBottom(x)
        .ticks(Math.ceil(d3.max(data, d => d.count)))
        .tickFormat(d3.format("d"))
        .tickSize(-chartHeight);

    const yAxis = d3.axisLeft(y);

    g.append("g")
        .selectAll(".bar")
        .data(data)
        .enter()
        .append("rect")
        .attr("class", "bar")
        .attr("x", 0)
        .attr("y", d => y(d.label))
        .attr("width", d => x(d.count))
        .attr("height", y.bandwidth())
        .attr("fill", "steelblue");

    g.append("g")
        .attr("class", "x-axis")
        .attr("transform", `translate(0,${chartHeight})`)
        .call(xAxis)
        .selectAll(".tick line")
        .attr("stroke", "#ddd");

    g.append("g")
        .attr("class", "y-axis")
        .call(yAxis);

    svg.selectAll(".x-axis path").remove();
    svg.selectAll(".x-axis line").remove();

    g.selectAll(".bar-label")
        .data(data)
        .enter()
        .append("text")
        .attr("class", "bar-label")
        .attr("x", d => x(d.count) + 5)
        .attr("y", d => y(d.label) + y.bandwidth() / 2 + 4)
        .text(d => d.count)
        .attr("fill", "black");

    // Add x-axis label
    g.append("text")
        .attr("class", "x-axis-label")
        .attr("x", chartWidth / 2)
        .attr("y", chartHeight + margin.bottom - 10)
        .attr("text-anchor", "middle")
        .text("Count");

    // Add y-axis label
    g.append("text")
        .attr("class", "y-axis-label")
        .attr("transform", `translate(-60, ${chartHeight / 2}) rotate(-90)`)
        .attr("text-anchor", "middle");
}

// BarChartWidget class
export class BarChartWidget {
    constructor({ id, data }) {
        this.id = id;
        this.data = Object.entries(data).map(([label, count]) => ({ label, count }));
        this.width = 400;
        this.height = 300;
    }

    compose() {
        // Create a new div element
        const div = document.createElement('div');
        div.id = this.id;
        div.className = "bar-chart-widget";

        // Add a heading to the div element
        const heading = document.createElement('h3');
        heading.textContent = "Distribution of States";
        div.appendChild(heading);

        // Create an SVG element inside the div
        const svg = d3.select(div).append("svg")
            .attr("width", "80%")
            .attr("height", "80%");

        // Call the drawBarChart function to render the bar chart
        window.setTimeout(() => drawBarChart(svg, this.data), 0);

        // Append the SVG element to the div
        return div;
    }
}
