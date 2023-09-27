// Surrogate autocomplete

/*
Called by: scripts/main.js

Important args:
- prefix
- callback

The response only contains at most 5 entries.

Response examples: 
["Adak Island, AK (ADK-Adak Island)", "Alexandria, LA (AEX-Alexandria Intl.)", "Brownsville, TX (BRO-South Padre Island Intl.)", "Cleveland, OH (CLE-Hopkins Intl.)", "Grand Forks, ND (GFK-Grand Forks Intl.)"]

The cache only contains a partial list of possible airports. Will just use that.
*/
$miniwob.surrogateAutocomplete = function (prefix, callback) {
  function match() {
    var query = prefix.toLowerCase().replace(/[^a-z0-9 ]/, '');
    var results = $miniwob.airports.filter(function (item) {
      return (item.toLowerCase().replace(/[^a-z0-9 ]/, '').includes(query));
    });
    callback(results.length ? results.slice(0, 5) : null);
  }

  if (!$miniwob.airports) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
      if (xhr.readyState == 4) {
        if (xhr.status == 200) {
          $miniwob.airports = JSON.parse(xhr.responseText);
          match();
        } else {
          console.error('Error loading airports.json');
        }
      }
    };
    xhr.open('GET', 'surrogate/airports.json');
    xhr.send();
  } else {
    match();
  }
}

