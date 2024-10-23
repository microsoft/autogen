// When body is ready
document.addEventListener('DOMContentLoaded', function() {
    // TODO: Please find a better way to override the button text in a better way...
    // Set a timer for 3 seconds to wait for the button to be rendered.
    setTimeout(function() {
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
