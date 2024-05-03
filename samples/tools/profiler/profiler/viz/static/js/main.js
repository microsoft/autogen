import { Message, MessageWidget, MessageHistoryWidget } from './widgets.js';
import { FilterWidget } from './widgets.js';
import { BarChartWidget } from './barchart.js';
import { TimelineWidget } from './timelines.js';

function renderFilters(data) {
    // Extract names of all the tags from the data
    const tags = data.reduce((acc, message) => {
        message.tags.forEach(tag => {
            if (!acc.includes(tag)) {
                acc.push(tag);
            }
        });
        return acc;
    }, []);

    const tagFilter = new FilterWidget({
        id: "tag-filter-widget",
        filterArray: tags
    });

    document.body.appendChild(tagFilter.render());

    return [tagFilter];
}

function updateAllWidgets(data) {
    const messageHistoryWidget = new MessageHistoryWidget({
        id: "message-history-widget",
        messageArray: data
    });

    const newWidgetElement = messageHistoryWidget.render();

    const existingWidgetElement = document.getElementById(newWidgetElement.id);

    if (existingWidgetElement) {
        // If the widget already exists, replace it with the new widget
        existingWidgetElement.replaceWith(newWidgetElement);
    } else {
        // If the widget does not exist, append it to the body
        document.body.appendChild(newWidgetElement);
    }

    // get mapping from states to counts
    const stateCounts = data.reduce((acc, message) => {
        message.states.forEach(state => {
            if (!acc[state]) {
                acc[state] = 0;
            }
            acc[state]++;
        });
        return acc;
    }, {});

    const barchart = new BarChartWidget({
        id: "bar-chart-widget",
        data: stateCounts
    });
    // document.body.appendChild(barchart.render());

    const existingBarChartElement = document.getElementById(barchart.id);
    if (existingBarChartElement) {
        existingBarChartElement.replaceWith(barchart.render());
    } else {
        document.body.appendChild(barchart.render());
    }


    const timelineWidget = new TimelineWidget({
        id: "timeline-widget",
        messageArray: data
    });

    const existingTimelineElement = document.getElementById(timelineWidget.id);
    if (existingTimelineElement) {
        existingTimelineElement.replaceWith(timelineWidget.render());
    } else {
        document.body.appendChild(timelineWidget.render());
    }
}

function getFilteredData(labels, data) {
    // Filter the data based on the labels
    // If labels is empty, return the original data
    if (labels.length === 0) {
        return data;
    }

    // Filter the data based on the labels
    // Include if any of the labels are in the tags
    return data.filter(message => {
        const tagMatch = labels.some(label => message.tags.includes(label));
        return tagMatch;
    });
}

function renderPage(data) {
    const filters = renderFilters(data);
    updateAllWidgets(data);

    // listen for the filterChanged event
    document.addEventListener('filterChanged', (event) => {
        // get all the filters that are checked
        // const checkedFilters = filters[0].getCheckedFilters();
        const checkedFilters = filters.reduce((acc, filter) => {
            return acc.concat(filter.getCheckedFilters());
        }, []);
        const filteredData = getFilteredData(checkedFilters, data);
        updateAllWidgets(filteredData);
    });
}

(function loadData() {
    // Load data from the path
    const path = 'data.json';

    // Fetch the data from the path
    fetch(path)
        .then(response => response.json())
        .then(data => renderPage(data));
})();
