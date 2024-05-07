
class State {
    /*
    A class to represent a state
    */
    constructor({name, description, tags}) {
        this.name = name;
        this.description = description;
        this.tags = tags;
    }

    static fromList(distList) {
        /*
        Create a list of State objects from a list of dictionaries
        */
        return distList.map(state => new State(state));
    }
}

class Message {
    /*
    A class to represent a message
    */
    constructor({id, source, content, tags}) {
        if (!id || !source || !content) {
            throw new Error('id, source, content are required fields');
        }
        this.id = id;
        this.source = source;
        this.content = content;
        if (!tags) {
            tags = [];
        }
        this.tags = tags;
    }
}

export class MessageProfile {
    /*
    A class to represent a message
    */
    constructor({message, states, cost, duration}) {
        if (!message || !states) {
            throw new Error('message, states are required fields');
        }
        this.message = new Message(message);
        this.states = State.fromList(states);
        if (!cost) {
            cost = -1;
        }
        this.cost = cost;
        if (!duration) {
            duration = -1;
        }
        this.duration = duration;
    }
}


class MessageWidget {

    constructor({
        id,
        msgProfile
    }) {
        this.id = id;
        this.msgProfile = msgProfile;
    }

    compose() {
        const div = document.createElement('div');
        div.className = "message-widget";
        div.id = this.id;
        const message = this.msgProfile.message;

        const h3 = document.createElement('h3');
        h3.textContent = message.source;
        div.appendChild(h3);

        const statesDiv = document.createElement('div');
        statesDiv.className = "states";
        this.msgProfile.states.forEach(state => {
            const span = document.createElement('span');
            span.className = "state";
            span.textContent = state.name;
            statesDiv.appendChild(span);
        });
        div.appendChild(statesDiv);

        const p = document.createElement('p');
        p.textContent = message.content;
        div.appendChild(p);

        const tagsDiv = document.createElement('div');
        tagsDiv.className = "tags";
        message.tags.forEach(tag => {
            const span = document.createElement('span');
            span.className = "tag";
            span.textContent = tag;
            tagsDiv.appendChild(span);
        });
        div.appendChild(tagsDiv);


        return div;
    }
}

export class MessageHistoryWidget {

    constructor({id, messageProfileArray}) {
        this.id = id;
        this.messageProfileArray = messageProfileArray;
    }

    compose() {
        const div = document.createElement('div');
        div.className = "message-history-widget";
        div.id = this.id;

        const heading = document.createElement('h3');
        heading.textContent = "Message History";
        div.appendChild(heading);

        this.messageProfileArray.forEach(profile => {
            const messageWidget = new MessageWidget({
                id: "message-" + profile.message.id,
                msgProfile: profile
            });
            div.appendChild(messageWidget.compose());
        });

        function scrollToElement(element) {
            const parent = element.parentElement;
            const startPos = parent.scrollTop;
            const topPos = element.offsetTop - parent.clientHeight / 2 + element.clientHeight / 2;
            const diff = topPos - startPos;

            let start;

            window.requestAnimationFrame(function step(timestamp) {
                if (!start) start = timestamp;
                // Elapsed milliseconds since start of scrolling.
                const time = timestamp - start;
                // Get percent of completion.
                const percent = Math.min(time / 500, 1); // 500ms duration

                parent.scrollTop = startPos + diff * percent;

                // Proceed with animation as long as we wanted it to.
                if (time < 500) {
                    window.requestAnimationFrame(step);
                }
            });
        }

        // Add a custom event listener to the div element
        window.addEventListener('messageClicked', (event) => {
            const message = event.detail.message;
            console.log("Message clicked: ", message);
            // scroll to the message with this id
            const messageDiv = div.querySelector(`#message-${message.id}`);
            console.log("Message div: ", messageDiv);
            if (messageDiv) {
                // messageDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                scrollToElement(messageDiv);
                // messageDiv.style.outline = "2px solid blue";

                const selectedMessages = div.querySelectorAll('.message-selected');
                selectedMessages.forEach(message => {
                    message.classList.remove('message-selected');
                })
                messageDiv.classList.add('message-selected');
            }
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

    compose() {
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

    compose() {
        const div = document.createElement('div');
        div.className = "filter-widget";
        div.id = this.id;

        const heading  = document.createElement('h3');
        heading.textContent = "Global Filters";
        div.appendChild(heading);

        this.filterArray.forEach(filter => {
            const filterWidget = new CheckboxFilter({
                id: filter,
                label: filter
            });
            div.appendChild(filterWidget.compose());
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
