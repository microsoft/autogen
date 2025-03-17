document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.copybtn').forEach(button => {
      // Return focus to copy button after activation
      button.addEventListener('click', async function(event) {
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

  // Set active TOCtree, version elements with aria-current=page
  document.querySelectorAll('.active').forEach(function(element) {
      element.setAttribute('aria-current', 'page');
  });

  // Set secondary navbar (in-page nagivation) active element with aria-current=page
  document.addEventListener("activate.bs.scrollspy", function () {
    const navLinks = document.querySelectorAll(".bd-toc-nav a");

    navLinks.forEach((navLink) => {
      navLink.parentElement.removeAttribute('aria-current');
    });

    const activeNavLinks = document.querySelectorAll(".bd-toc-nav a.active");
    activeNavLinks.forEach((navLink) => {
      navLink.parentElement.setAttribute('aria-current', 'page');
    });
  });
});

async function copyToClipboard(button) {
  const targetSelector = button.getAttribute('data-clipboard-target');
  const codeBlock = document.querySelector(targetSelector);
  try {
      await navigator.clipboard.writeText(codeBlock.textContent);
  } catch (err) {
      console.error('Failed to copy text: ', err);
  }
}