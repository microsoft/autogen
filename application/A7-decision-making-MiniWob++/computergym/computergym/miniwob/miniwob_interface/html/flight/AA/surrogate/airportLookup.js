// Surrogate autocomplete

/*
Called by: apps/common/js/jquery/aacom/plugins/aaAirportAutoComplete.js

Important args:
- input.data.searchText: search term
- input.success: callback

Response examples: home/ajax/airportLookup_*
[{"name":"Baltimore Washington International Airport","code":"BWI","stateCode":"MD","countryCode":"US","countryName":"United States"},...]
*/
$miniwob.surrogateAutocomplete = function (input) {
  function match() {
    var query = input.data.searchText.toLowerCase().replace(/[^a-z0-9]/, '');
    var results = $miniwob.airports.filter(function (item) {
      return (item.code.toLowerCase().includes(query));
    });
    if (!results.length) {
      results = $miniwob.airports.filter(function (item) {
        var name = (item.name + item.stateCode).toLowerCase().replace(/[^a-z0-9]/, '');
        return name.includes(query);
      });
    }
    input.success(results);
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
