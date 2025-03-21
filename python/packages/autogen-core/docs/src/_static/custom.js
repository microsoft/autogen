document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.copybtn').forEach(button => {
    // Return focus to copy button after activation
    button.addEventListener('click', async function (event) {
      // Save the current focus
      const focusedElement = document.activeElement;

      // Perform the copy action
      await copyToClipboard(this);

      // Restore the focus
      focusedElement.focus();
    });
  });

  document.querySelectorAll('.search-button-field').forEach(button => {
    button.addEventListener('click', () => {
      // Save the element that had focus before opening the search
      const previousFocus = document.activeElement;

      // Add an event listener to handle closing the search
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          // Restore focus to the previous element
          previousFocus.focus();
        }
      });
    });
  });
});

async function copyToClipboard(button) {
  const targetSelector = button.getAttribute('data-clipboard-target');
  const codeBlock = document.querySelector(targetSelector);
  try {
    await navigator.clipboard.writeText(codeBlock.textContent);

    // Add a visually hidden element for screen readers to announce
    const srAnnouncement = document.createElement('div');
    srAnnouncement.textContent = 'Copied to clipboard';
    srAnnouncement.setAttribute('role', 'status');
    srAnnouncement.setAttribute('aria-live', 'polite');
    srAnnouncement.style.position = 'absolute';
    srAnnouncement.style.width = '1px';
    srAnnouncement.style.height = '1px';
    srAnnouncement.style.padding = '0';
    srAnnouncement.style.margin = '-1px';
    srAnnouncement.style.overflow = 'hidden';
    srAnnouncement.style.clipPath = 'inset(50%)';
    srAnnouncement.style.whiteSpace = 'nowrap';
    srAnnouncement.style.border = '0';

    document.body.appendChild(srAnnouncement);

    // Remove the announcement element after it's been read
    setTimeout(() => {
      document.body.removeChild(srAnnouncement);
    }, 3000);
  } catch (err) {
    console.error('Failed to copy text: ', err);
  }
}
