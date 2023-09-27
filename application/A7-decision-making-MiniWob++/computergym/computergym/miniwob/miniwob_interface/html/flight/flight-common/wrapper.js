// ################################################
// Additional methods for flight domain

core.flightChildWindow = function () {
  return document.getElementById('wrap').contentWindow;
}

window.addEventListener('load', function () {
  var correctLocation = null;

  document.getElementById('wrap').addEventListener('load', function (event) {
    var currentLocation = this.contentWindow.location.href;
    if (correctLocation === null) {
      correctLocation = currentLocation;
    } else if (correctLocation != currentLocation) {
      if (core.EP_TIMER !== null) {
        document.getElementById('reward-reason').innerHTML = (
          '<b>BAD:</b> Navigated away to ' + currentLocation);
      }
      core.endEpisode(-1, false, 'BAD: Navigated away to ' + currentLocation);
      return;
    }
    if (recorder.isRecording) {
      // Tell the child to register event listeners
      core.flightChildWindow().$miniwob.recorder.setup();
    }
  });

});

// ################################################
// Dataset and validation

// The child page should call this method on form submit
core.flightSubmit = function (data, recorder_data) {
  var reward = core.validateForm(data);
  var reason = document.getElementById('reward-reason').textContent;
  core.endEpisode(reward, false, reason, recorder_data);
}

/**
  Overrides genProblem.
  Set core.currentQuestion as a sampled problem. Also starts the task.
  Does not return anything.
  */
var genProblem = function () {
  core.currentQuestion = core.sampleQuestion();
  var instruction = core.currentQuestion.instruction;
  document.getElementById('query').textContent = JSON.stringify(instruction);
  var queryPretty = [];
  Object.keys(instruction).forEach(function (key) {
    queryPretty.push('<tr><th>' + key + '</th><td>' + instruction[key] + '</td>');
  });
  document.getElementById('query-pretty').innerHTML = (
      '<div class=mode>Mode: ' + WOB_DATA_MODE + '</div>' +
      '<table>' + queryPretty.join('') + '</table>');
  document.getElementById('reward-reason').innerHTML = '';
  WOB_TASK_READY = false;   // The child page must set this to true
  document.getElementById('wrap').src = 'index.html';
}

/**
  Return an object that looks like this:
  {
    "instruction": {"key1", "value1", ...}
    "request": {"key1", "value1", ...}
  }
*/
core.sampleQuestion = function () {
  if (WOB_DATA_MODE == 'train' || WOB_DATA_MODE == 'default')
    return core.sample(DATA_TRAIN);
  else if (WOB_DATA_MODE == 'test')
    return core.sample(DATA_TEST);
  else
    throw 'Incorrect WOB_DATA_MODE';
}

// List of required fields
// The reward is -1 if any of these fields is not filled
core.requiredFields = [];

/**
  Validate the form and return the reward.
  data format: list of [tag, type, name, value]
*/
core.validateForm = function(data) {
  // Convert to a dict
  var dataDict = {};
  data.forEach(function (datum) {
    dataDict[datum[2]] = datum[3];
  });
  // Compute accuracy 
  var target = core.currentQuestion.request;
  var score = 0., n = 0., wrongFields = [];
  for (var key in target) {
    n++;
    var expected = target[key], predicted = dataDict[key],
        check = (expected == predicted);
    console.log([check, key, expected, predicted]);
    if (!check) {
      wrongFields.push(
          '<b>' + key + '</b><br>True: ' + expected + '<br>Pred: ' + predicted);
    }
    score += check;
  }
  // Validate the required fields
  if (!core.validateRequiredFields(dataDict)) return -1;
  // Display reasons
  if (score == n) {
    document.getElementById('reward-reason').innerHTML = '<b>GOOD</b>';
  } else {
    document.getElementById('reward-reason').innerHTML = (
        '<b>PARTIAL:</b> Incorrect fields:<br>' + wrongFields.join('<br>'));
  }
  return score / n;
}

core.validateRequiredFields = function(dataDict) {
  for (var i = 0; i < core.requiredFields.length; i++) {
    var key = core.requiredFields[i];
    if (!(dataDict[key] || '').length) {
      console.log(['missing required field', key]);
      document.getElementById('reward-reason').innerHTML = (
        '<b>BAD:</b> Missing required field ' + key);
      return false;
    }
  }
  return true;
}

// ################################################
// Function overrides (delegate to the iframe)

core.getDOMInfo = function () {
  return core.flightChildWindow().$miniwob.getDOMInfo();
}

core.elementClick = function (ref) {
  return core.flightChildWindow().$miniwob.elementClick(ref);
}

// ################################################
// Record demonstrations

var recorder = {};
recorder.SERVER_DEFAULT = 'http://localhost:8032';
recorder.DISPLAY_HTML = `
  <div class="info">
    <label>Server URL:</label>
    <span id='server-name'>-</span>
  </div>
  <div class="info">
    <label>Server reply:</label>
    <span id='server-reply'>-</span>
  </div>
`;

recorder.setup = function () {
  if (recorder.isSetup) return;
  document.getElementById('reward-display').innerHTML += recorder.DISPLAY_HTML;
  recorder.server = (core.QueryString.server || recorder.SERVER_DEFAULT) + '/record';
  document.getElementById('server-name').innerHTML = recorder.server;
  var url = window.location.pathname;
  recorder.taskName = (/flight\/[^/]*/.exec(url) || ['flight.unknown'])[0].replace(/\//, '.');
  recorder.isSetup = true;
}

recorder.startRecording = function (startEpisodeReal) {
  recorder.data = {};
  recorder.data.taskName = recorder.taskName;
  recorder.data.states = [];
  recorder.isRecording = true;
  startEpisodeReal();
  var utterance = core.getUtterance();
  if (typeof utterance === 'string') {
    recorder.data.utterance = utterance;
  } else {
    recorder.data.utterance = utterance.utterance;
    recorder.data.fields = utterance.fields;
  }
}

// End recording the episode
recorder.endRecording = function () {
  recorder.data.reward = WOB_REWARD_GLOBAL;
  recorder.data.rawReward = WOB_RAW_REWARD_GLOBAL;
  // Send the data to the server
  recorder.isRecording = false;
  var data = recorder.data;
  recorder.data = {};   // Prevent future addition
  console.log(data);
  var req = new XMLHttpRequest();
  req.open('POST', recorder.server);
  req.setRequestHeader('Content-type', 'text/plain');
  req.onreadystatechange = function () {
    if (req.readyState === XMLHttpRequest.DONE) {
      var msg = document.getElementById('server-reply');
      if (req.status === 200) {
        msg.setAttribute('style', 'color:green');
        msg.textContent = 'OK: ' + req.responseText;
      } else {
        msg.setAttribute('style', 'color:red');
        msg.textContent = 'ERROR: ' + req.statusText;
      }
    }
  }
  req.send(JSON.stringify(data));
  // Make it ready for the next episode
  core.cover_div.classList.remove('transparent');
}

// Enable demonstration recording with "?flightRecord=..." in the URL
if (core.QueryString.flightRecord) {

  // Wrap startEpisodeReal
  core.startEpisodeReal = (function(startEpisodeReal) {
    return function () {
      if (core.cover_div.classList.contains('transparent')) return;
      recorder.setup();
      recorder.startRecording(startEpisodeReal);
    }
  })(core.startEpisodeReal);

  // Wrap endEpisode
  core.endEpisode = (function(endEpisode) {
    return function (reward, time_proportional, reason, recorder_data) {
      if (core.EP_TIMER === null) return;
      core.cover_div.classList.add('transparent');
      endEpisode(reward, time_proportional, reason);
      // Delay to allow the last action to be recorded
      if (recorder_data) {
        recorder.data.states = recorder_data.states;
      }
      setTimeout(recorder.endRecording, 500);
    }
  })(core.endEpisode);

}
