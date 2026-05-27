window.addEventListener("map:init", function (event) {
  var map = event.detail.map;

  // 1. Initialize the Search Box (Geocoder) with Mapbox
  var geocoder = L.Control.geocoder({
    geocoder: L.Control.Geocoder.mapbox({ apiKey: 'pk.eyJ1IjoibGVlcm95bTkiLCJhIjoiY21vYTZjaGx4MDQ5djJzcXl0bGpxbGRwaSJ9.pgjKuxq6py5bUrTv_E9M8Q' }),
    defaultMarkGeocode: false,
    placeholder: "Search for landmarks, streets, districts...",
  }).addTo(map);

  // 2. What happens when you select a search result:
  geocoder.on("markgeocode", function (e) {
    var latlng = e.geocode.center;
    var address = e.geocode.name; // The human-readable address

    // Move the map to the searched location
    map.setView(latlng, 15);

    // AUTO-FILL MAGIC: Type the address into the Django 'Location Name' field!
    var locationNameInput = document.getElementById("id_location_name");
    if (locationNameInput) {
      locationNameInput.value = address;
    }

    // UPDATE THE DATABASE FIELD: Format coordinates for Django PostGIS
    var geojson = {
      type: "Point",
      coordinates: [latlng.lng, latlng.lat],
    };
    var hiddenLocationInput = document.getElementById("id_location");
    if (hiddenLocationInput) {
      hiddenLocationInput.value = JSON.stringify(geojson);
    }

    // DROP THE VISUAL PIN
    if (map.drawnItems) {
      map.drawnItems.clearLayers();
      var marker = L.marker(latlng);
      map.drawnItems.addLayer(marker);
    }
  });
});
