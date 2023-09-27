// ################################################
// Record demonstrations

/* POST submit format

* utterance
* states: array of objects with the following keys:
  - time: time elapsed
  - dom: DOM structure
  - action: action performed at that moment
* reward

*/

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

// Add event listeners
recorder.LISTENERS = [
  'click',
  // 'dblclick',
  'mousedown',
  'mouseup',
  // 'keypress',
  // 'scroll',
];
recorder.setup = function () {
  if (recorder.isSetup) return;
  document.getElementById('reward-display').innerHTML += recorder.DISPLAY_HTML;
  recorder.LISTENERS.forEach(function (name) {
    document.addEventListener(name, recorder['on' + name], true);
    document.addEventListener(name, recorder['on' + name], false);
  });
  recorder.server = (core.QueryString.server || recorder.SERVER_DEFAULT) + '/record';
  document.getElementById('server-name').innerHTML = recorder.server;
  var url = window.location.pathname;
  recorder.taskName = url.substr(url.lastIndexOf('/') + 1).replace(/\.html/, '');
  recorder.isSetup = true;
}

// Start recording the episode
recorder.startRecording = function () {
  recorder.data = {};
  recorder.data.taskName = recorder.taskName;
  var utterance = core.getUtterance();
  if (typeof utterance === 'string') {
    recorder.data.utterance = utterance;
  } else {
    recorder.data.utterance = utterance.utterance;
    recorder.data.fields = utterance.fields;
  }
  recorder.data.states = [];
  recorder.isRecording = true;
  recorder.addState(null, null);
}

function rgba2rgb(rgba) {
  var rgb = []
  for (var i = 0; i < rgba.length; i += 4) {
    rgb.push([rgba[i], rgba[i + 1], rgba[i + 2]])
  }
  return rgb
}

// Add a state to the recording data
recorder.addState = function (event, action) {
  if (!recorder.isRecording) return;
  if (event && action)
    action.timing = event.eventPhase;
  // console.log('Adding state', action);
  console.log(recorder.imageCapture.track.readyState)
  console.log(recorder.imageCapture.track.enabled)
  console.log(recorder.imageCapture.track.muted)
  if (!(recorder.imageCapture.track.readyState != 'live' || !recorder.imageCapture.track.enabled || recorder.imageCapture.track.muted)) {
    recorder.takeSnapshot().then(imagebitmap => {
      let canvas = document.createElement('canvas')
      canvas.width = 160
      canvas.height = 210
      let context = canvas.getContext('2d')

      context.drawImage(imagebitmap, 0, 111, imagebitmap.width, imagebitmap.height, 0, 0, imagebitmap.width, imagebitmap.height)
      var imgData = context.getImageData(0, 0, canvas.width, canvas.height).data;

      var state = {
        'time': new Date().getTime() - core.ept0,
        'action': action,
        'image': rgba2rgb(Array.from(imgData))
      };
      state.dom = core.getDOMInfo();

      recorder.data.states.push(state);
    }).catch(error => console.log(error));
  }
  if (event)
    event.target.dataset.recording_target = true;

  if (event)
    delete event.target.dataset.recording_target;
}

/*
let pre_x = 0
let pre_y = 0
recorder.onmousemove = async function (event) {
  if (event.target === core.cover_div ||
    event.pageX >= 160 || event.pageY >= 210)
    return;


  if (pre_x < event.pageX) {
    recorder.addState(event, {
      "type": "right",
      "x": event.pageX,
      "y": event.pageY,
    });
  } else if (pre_x > event.pageX) {
    recorder.addState(event, {
      "type": "left",
      "x": event.pageX,
      "y": event.pageY,
    });
  }

  if (pre_y < event.pageY) {
    recorder.addState(event, {
      "type": "down",
      "x": event.pageX,
      "y": event.pageY,
    });
  } else if (pre_y > event.pageY) {
    recorder.addState(event, {
      "type": "up",
      "x": event.pageX,
      "y": event.pageY,
    });
  }

  pre_x = event.pageX
  pre_y = event.pageY
}
*/

// Actions
recorder.ondblclick = function (event) {
  if (event.target === core.cover_div ||
    event.pageX >= 160 || event.pageY >= 210)
    return;
  recorder.addState(event, {
    'type': 'dblclick',
    'x': event.pageX,
    'y': event.pageY,
  });
}
recorder.onclick = function (event) {
  if (event.target === core.cover_div ||
    event.pageX >= 160 || event.pageY >= 210)
    return;
  recorder.addState(event, {
    'type': 'click',
    'x': event.pageX,
    'y': event.pageY,
  });
}
recorder.onmousedown = function (event) {
  if (event.target === core.cover_div ||
    event.pageX >= 160 || event.pageY >= 210)
    return;
  recorder.addState(event, {
    'type': 'mousedown',
    'x': event.pageX,
    'y': event.pageY,
  });
}
recorder.onmouseup = function (event) {
  if (event.target === core.cover_div ||
    event.pageX >= 160 || event.pageY >= 210)
    return;
  recorder.addState(event, {
    'type': 'mouseup',
    'x': event.pageX,
    'y': event.pageY,
  });
}

/*
recorder.onkeypress = async function (event) {
  recorder.addState(event, {
    'type': 'keypress',
    'keyCode': event.keyCode,
    'charCode': event.charCode,
  });
}

recorder.onscroll = async function (event) {
  // Scroll is super redundant; only keep the first one
  if (recorder.data.states.length) {
    var lastState = recorder.data.states[recorder.data.states.length - 1];
    if (lastState.action && lastState.action.type === 'scroll')
      return;
    //recorder.data.states.pop();     // <-- use this for keeping the last one
  }
  recorder.addState(event, {
    'type': 'scroll',
  });
}
*/

// End recording the episode
recorder.endRecording = function () {
  recorder.data.reward = WOB_REWARD_GLOBAL;
  recorder.data.rawReward = WOB_RAW_REWARD_GLOBAL;
  // Send the data to the server
  recorder.isRecording = false;
  var data = recorder.data;
  recorder.data = {};   // Prevent future addition
  // console.log(data);
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

// ################################
// Wrappers
recorder.imageCapture = null
// Wrap startEpisodeReal
core.startEpisodeReal = (function (startEpisodeReal) {
  return function () {
    if (core.cover_div.classList.contains('transparent')) return;
    recorder.setup();
    recorder.startCapture().then(() => {
      recorder.startRecording();
      startEpisodeReal();
    })
      .catch(err => {
        console.log(err);
      });



  }
})(core.startEpisodeReal);

// Wrap endEpisode
core.endEpisode = (function (endEpisode) {
  return function (reward, time_proportional, reason) {
    if (core.EP_TIMER === null) return;
    core.cover_div.classList.add('transparent');

    endEpisode(reward, time_proportional, reason);
    // Delay to allow the last action to be recorded
    setTimeout(recorder.endRecording, 500);
  }
})(core.endEpisode);

// ################################################################
// Screnn capture
recorder.captureStream = null
// 화면캡쳐(video)를 시작하는 함수
recorder.startCapture = async function () {
  try {
    const displayMediaOptions = { audio: false, video: { cursor: 'never' } }
    recorder.captureStream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions)
    recorder.track = recorder.captureStream.getVideoTracks()[0];
    recorder.imageCapture = new ImageCapture(recorder.track);
  } catch (err) {
    console.error(err)
  }

  return
}


// 화면캡쳐를 중지하는 함수
recorder.stopCapture = function () {
  const tracks = recorder.captureStream.getTracks()
  tracks.forEach((track) => track.stop())
}

// 스냅샷을 찍는 함수
recorder.takeSnapshot = function () {
  try {
    const image = recorder.imageCapture.grabFrame();
    return image
  }
  catch (err) {
    console.log(err)
  }

}
