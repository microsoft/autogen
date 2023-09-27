// Utilities for the child page
var $miniwob = {};

// ################################################
// FAKE DATE (before anything else loads)

// Inspired by https://stackoverflow.com/a/44497384
// Shift the date by a certain offset
(function (year, month, day) {
  var startTime = Date.now();
  var fakeTime = new Date(year, month, day).getTime();
  var __Date = Date;
  Date = function() {
    if (arguments.length > 0) {
      return new __Date(...arguments);
    } else {
      return new __Date(__Date.now() - startTime + fakeTime);
    }
  }
  Date.prototype = __Date.prototype;
})(
  // 2 is actually March
  2017, 2, 1
);

// ################################################
// Intercept events

window.addEventListener('load', function () {

  // Intercept form submission
  // The form must have class name 'miniwob-main-form'
  // Inspired by https://code.google.com/archive/p/form-serialize/
  var form = document.getElementsByClassName('miniwob-main-form')[0];
  form.addEventListener('submit', function (event) {
    var data = [];
    [].forEach.call(form.elements, function (elt, i) {
      if (!elt.name) return;
      switch (elt.tagName) {
        case 'INPUT':
          switch (elt.type) {
            case 'checkbox':
            case 'radio':
              if (elt.checked) {
                data.push([elt.tagName, elt.type, elt.name, elt.value]);
              }
              break;
            default:
              data.push([elt.tagName, elt.type, elt.name, elt.value]);
              break;
          }
          break;
        case 'TEXTAREA':
          data.push([elt.tagName, elt.type, elt.name, elt.value]);
          break;
        case 'SELECT':
          switch (elt.type) {
            case 'select-multiple':
              [].forEach.call(elt.options, function (opt) {
                if (opt.selected)
                  data.push([elt.tagName, elt.type, elt.name, opt.value]);
              });
              break;
            default:
              data.push([elt.tagName, elt.type, elt.name, elt.value]);
          }
          break;
        case 'BUTTON':
          switch (elt.type) {
            case 'reset':
            case 'submit':
            case 'button':
              data.push([elt.tagName, elt.type, elt.name, elt.value]);
              break;
          }
          break;
      }
    });
    window.parent.core.flightSubmit(data, $miniwob.recorder.data);
    event.preventDefault();
    return false;
  });

  // Loaded!
  window.parent.WOB_TASK_READY = true;

});

// ################################################
// getDOMInfo reimplemented here

$miniwob.previousDOMInfo = {};
$miniwob.nextRefCode = 1;
$miniwob.nextTextRefCode = -1;
$miniwob.resetRefCode = function () {
  $miniwob.nextRefCode = 1;
  $miniwob.nextTextRefCode = -1;
}

/* Returns a nested object (dict) with all visible DOM element information.

   Special handling for Text nodes:
   - Text nodes with only whitespaces are discarded.
   - If the Text node is the only child, discard that Text node
     and reassign its text to the parent Element.
   - If the Text node is not the only child, it is broken into
     pseudo-Elements with tag "t".

   Assume that the page is refreshed before each episode.
*/
$miniwob.getDOMInfo = function (baseElement) {
  $miniwob.previousDOMInfo = {}

  function getDOMInfoOfElement(element) {
    var rect = element.getBoundingClientRect();
    if (rect.width == 0 || rect.height == 0) return;
    var answer = {
      tag: element.tagName,
      left: rect.left, top: rect.top,
      width: rect.width, height: rect.height,
      children: [],
      id: element.id,
      classes: element.className,
    };
    // Assign ref code
    if (element.dataset.wob_ref !== undefined) {
      answer.ref = +element.dataset.wob_ref;
    } else {
      element.dataset.wob_ref = answer.ref = $miniwob.nextRefCode++;
    }
    // Record styles
    var computedStyle = window.getComputedStyle(element);
    answer.bgColor = computedStyle.backgroundColor;
    answer.fgColor = computedStyle.color;
    // Indicate if the element is being focused on
    if (document.activeElement === element) {
      answer.focused = true;
    }
    // Indicate if the element is tampered with in this episode
    if (element.dataset.tampered !== undefined) {
      answer.tampered = true;
    }
    // For recording demonstrations: Record the target
    if (element.dataset.recording_target) {
      answer.recordingTarget = true;
    }
    // For <input>, also add input type and value
    if (element instanceof HTMLInputElement) {
      var inputType = element.type;
      answer.tag += '_' + inputType;
      if (inputType === 'checkbox' || inputType === 'radio') {
        answer.value = element.checked;
      } else {
        answer.value = element.value;
      }
    } else if (element instanceof HTMLTextAreaElement) {
      answer.value = element.value;
    }
    $miniwob.previousDOMInfo[answer.ref] = element;
    // Read the children
    var filteredChildNodes = [], textOnly = true;
    element.childNodes.forEach(function (child) {
      if (child instanceof Text) {
        if (!/^\s*$/.test(child.data)) {
          filteredChildNodes.push(child);
        }
      } else if (child instanceof Element) {
        filteredChildNodes.push(child);
        textOnly = false;
      }
    });
    if (textOnly) {
      answer.text = filteredChildNodes.map(function (x) {
        return x.data.trim();
      }).join(' ');
    } else {
      filteredChildNodes.forEach(function (child) {
        if (child instanceof Text) {
          addDOMInfosOfTextNode(child, answer.children);
        } else {
          child = getDOMInfoOfElement(child);
          if (child !== undefined)
            answer.children.push(child);
        }
      });
    }
    return answer;
  }

  function addDOMInfosOfTextNode(textNode, collection) {
    // Break the text node into multiple nodes
    // Each node only occupies a single rectangle boundary
    var range = document.createRange();
    range.selectNodeContents(textNode);
    var absolute_start = range.startOffset, absolute_end = range.endOffset;
    var start = absolute_start;
    var itr = 0;
    while (start < absolute_end) {
      // Binary search on the next end point
      var end_lower_bound = start + 1,
          end_upper_bound = absolute_end,
          l = range.getClientRects().length,
          end = Math.floor((end_lower_bound * (l-1) + end_upper_bound) / l);
      while (end_lower_bound <= end_upper_bound) {
        range.setEnd(textNode, end);
        if (range.getClientRects().length == 1) {
          end_lower_bound = end + 1;
          end = Math.min(end_lower_bound + 5, Math.floor((end_lower_bound + end_upper_bound) / 2));
        } else {
          end_upper_bound = end - 1;
          end = Math.max(end_upper_bound - 5, Math.floor((end_lower_bound + end_upper_bound) / 2));
        }
        if (itr++ > 1000) throwTextNodeError('Text node computation stuck in an infinite loop');
      }
      range.setEnd(textNode, end);
      var rects = range.getClientRects();
      if (rects.length !== 1) throwTextNodeError('Text node computation incorrect');
      var rect = rects[0], text = textNode.data.substring(start, end).trim();
      if (rect.width > 0 && rect.height > 0 && text) {
        var answer = {
          tag: "t",
          left: rect.left, top: rect.top,
          width: rect.width, height: rect.height,
          ref: $miniwob.nextTextRefCode--,
          children: [],
          text: text,
        };
        collection.push(answer);
      }
      start = end;
      range.setEnd(textNode, absolute_end);
      range.setStart(textNode, start);
      if (itr++ > 1000) throwTextNodeError('Text node computation stuck in an infinite loop');
    }
  }

  function throwTextNodeError(message) {
    alert(message);
    throw message;
  }

  return getDOMInfoOfElement(baseElement || document.body);
}

/* Click on an element regardless of its location or visibility.

   Args:
     ref: The ref value generated by the previous call to getDOMInfo
*/
$miniwob.elementClick = function (ref) {
  try {
    var element = $miniwob.previousDOMInfo[ref];
    element.click();
    element.focus();
    return true;
  } catch (err) {
    return err.message;
  }
}

// ################################################
// Record demonstrations

// Add event listeners
$miniwob.recorder = {}
$miniwob.recorder.LISTENERS = [
  'click',
  'dblclick',
  'mousedown',
  'mouseup',
  'keypress',
  'keydown',
  'keyup',
  'scroll',
];
$miniwob.recorder.setup = function () {
  $miniwob.recorder.startTime = new Date().getTime();
  $miniwob.recorder.data = {states: []};
  $miniwob.recorder.LISTENERS.forEach(function (name) {
    document.addEventListener(name, $miniwob.recorder['on' + name], true);
    document.addEventListener(name, $miniwob.recorder['on' + name], false);
  });
  $miniwob.recorder.isRecording = true;
  $miniwob.recorder.addState(null, null);
}

// Add a state to the recording data
$miniwob.recorder.addState = function (event, action) {
  if (!$miniwob.recorder.isRecording) return;
  if (event && action)
    action.timing = event.eventPhase;
  console.log('Adding state', action);
  var state = {
    'time': new Date().getTime() - $miniwob.recorder.startTime,
    'action': action,
  };
  if (event && event.target && event.target.dataset)
    event.target.dataset.recording_target = true;
  state.dom = $miniwob.getDOMInfo();
  if (event && event.target && event.target.dataset)
    delete event.target.dataset.recording_target;
  $miniwob.recorder.data.states.push(state);
}

// Actions
$miniwob.recorder.ondblclick = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'dblclick',
    'x': event.pageX, 'cx': event.clientX,
    'y': event.pageY, 'cy': event.clientY,
  });
}
$miniwob.recorder.onclick = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'click',
    'x': event.pageX, 'cx': event.clientX,
    'y': event.pageY, 'cy': event.clientY,
  });
}
$miniwob.recorder.onmousedown = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'mousedown',
    'x': event.pageX, 'cx': event.clientX,
    'y': event.pageY, 'cy': event.clientY,
  });
}
$miniwob.recorder.onmouseup = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'mouseup',
    'x': event.pageX, 'cx': event.clientX,
    'y': event.pageY, 'cy': event.clientY,
  });
}

$miniwob.recorder.onkeypress = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'keypress',
    'keyCode': event.keyCode,
    'charCode': event.charCode,
  });
}
$miniwob.recorder.onkeydown = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'keydown',
    'keyCode': event.keyCode,
    'charCode': event.charCode,
  });
}
$miniwob.recorder.onkeyup = function (event) {
  $miniwob.recorder.addState(event, {
    'type': 'keyup',
    'keyCode': event.keyCode,
    'charCode': event.charCode,
  });
}

$miniwob.recorder.onscroll = function (event) {
  // Scroll is super redundant; only keep the first one
  if ($miniwob.recorder.data.states.length) {
    var lastState = $miniwob.recorder.data.states[$miniwob.recorder.data.states.length - 1];
    if (lastState.action && lastState.action.type === 'scroll')
      return;
      //$miniwob.recorder.data.states.pop();     // <-- use this for keeping the last one
  }
  $miniwob.recorder.addState(event, {
    'type': 'scroll',
  });
}
