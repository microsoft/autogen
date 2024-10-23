// When body is ready
document.addEventListener('DOMContentLoaded', function() {
    // TODO: Please find a better way to override the button text in a better way...
    // Set a timer for 3 seconds to wait for the button to be rendered.
    setTimeout(async function() {

        // Fetch version list
        // https://raw.githubusercontent.com/microsoft/autogen/refs/heads/main/docs/switcher.json
        const response = await fetch('https://raw.githubusercontent.com/microsoft/autogen/refs/heads/main/docs/switcher.json');
        const data = await response.json();

        // Find the entry where preferred is true
        const preferred = data.find(entry => entry.preferred);
        if (preferred) {
            // Get current rendered version
            const currentVersion = DOCUMENTATION_OPTIONS.VERSION;
            const urlVersionPath = DOCUMENTATION_OPTIONS.theme_switcher_version_match;
            // The version compare library seems to not like the dev suffix without - so we're going to do an exact match and hide the banner if so
            // For the "dev" version which is always latest we don't want to consider hiding the banner
            if ((currentVersion === preferred.version) && (urlVersionPath !== "dev")) {
                // Hide the banner with id bd-header-version-warning
                document.getElementById('bd-header-version-warning').style.display = 'none';
                return;
            }
        }

        // Get the button with class "pst-button-link-to-stable-version". There is only one.
        var button = document.querySelector('.pst-button-link-to-stable-version');
        if (!button) {
            // If the button is not found, return.
            return;
        }
        // Set the button's text to "Switch to latest dev release"
        button.textContent = "Switch to latest dev release";
    }, 500);
});
