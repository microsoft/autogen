
export class Message {

    /*
    A class to represent a message
    */

    constructor(id, source, content, tags, states) {
        this.id = id;
        this.source = source;
        this.content = content;
        this.tags = tags;
        this.states = states;
    }
}

export class MessageWidget {

    constructor({
        id,
        message
    }) {
        this.id = id;
        this.message = message;
    }

    render() {
        const div = document.createElement('div');
        div.className = "message-widget";
        div.id = `message-${this.id}`;

        const h3 = document.createElement('h3');
        h3.textContent = this.message.source;
        div.appendChild(h3);

        const p = document.createElement('p');
        p.textContent = this.message.content;
        div.appendChild(p);

        const tagsDiv = document.createElement('div');
        tagsDiv.className = "tags";
        this.message.tags.forEach(tag => {
            const span = document.createElement('span');
            span.className = "tag";
            span.textContent = tag;
            tagsDiv.appendChild(span);
        });
        div.appendChild(tagsDiv);

        const statesDiv = document.createElement('div');
        statesDiv.className = "states";
        this.message.states.forEach(state => {
            const span = document.createElement('span');
            span.className = "state";
            span.textContent = state;
            statesDiv.appendChild(span);
        });
        div.appendChild(statesDiv);

        return div;
    }
}

export class MessageHistoryWidget {

    constructor({id, messageArray}) {
        this.id = id;
        this.messageArray = messageArray;
    }

    render() {
        const div = document.createElement('div');
        div.className = "message-history-widget";
        div.id = this.id;

        const heading = document.createElement('h3');
        heading.textContent = "Message History";
        div.appendChild(heading);

        this.messageArray.forEach(message => {
            const messageWidget = new MessageWidget({
                id: message.id,
                message: message
            });
            div.appendChild(messageWidget.render());
        });

        return div;
    }
}

class CheckboxFilter {

    constructor ({
        id,
        label
    }){
        this.id = id;
        this.label = label;
    }

    render() {
        const div = document.createElement('div');
        div.className = "checkbox-filter";
        div.id = this.id;

        const input = document.createElement('input');
        input.type = "checkbox";
        input.id = "filter-" + this.id;
        input.name = this.id;
        input.value = this.id;

        // Add event listener for 'change' event on the input element
        // Dispatch a custom event 'filterChanged' with the filter and isChecked as detail
        input.addEventListener('change', (event) => {

            const customEvent = new CustomEvent('filterChanged', {
                bubbles: true,
                detail: {
                    filter: this.id,
                    isChecked: event.target.checked
                }
            });
            div.dispatchEvent(customEvent);
        });

        div.appendChild(input);

        const label = document.createElement('label');
        label.htmlFor = this.id;
        label.textContent = this.label;
        div.appendChild(label);

        return div;
    }
}

export class FilterWidget {

    /*
    Creates a filter widget containing
    a check box for each filter in the filterArray
    */

    constructor({
        id,
        filterArray
    }) {
        this.id = id;
        this.filterArray = filterArray;
    }

    render() {
        const div = document.createElement('div');
        div.className = "filter-widget";
        div.id = this.id;

        const heading  = document.createElement('h3');
        heading.textContent = "Filters";
        div.appendChild(heading);

        this.filterArray.forEach(filter => {
            const filterWidget = new CheckboxFilter({
                id: filter,
                label: filter
            });
            div.appendChild(filterWidget.render());
        });

        return div;
    }

    getCheckedFilters() {
        /*
        Return the labels of all the checked filters
        */
        const checkedFilters = [];

        this.filterArray.forEach(filter => {

            // get labels of all checkboxes
            const checkbox = document.getElementById(`filter-${filter}`);
            if (checkbox.checked) {
                checkedFilters.push(filter);
            }
        });
        return checkedFilters;
    }
}
