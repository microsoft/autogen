document.addEventListener('DOMContentLoaded', function () {
  let liveRegion = createLiveRegion();

  document.querySelectorAll('.copybtn').forEach(button => {
    // Return focus to copy button after activation
    button.addEventListener('click', async function (event) {
      // Save the current focus
      const focusedElement = document.activeElement;

      // Perform the copy action
      await copyToClipboard(this);
      announceMessage(liveRegion, 'Copied to clipboard');

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

  // Set active TOCtree elements with aria-current=page
  document.querySelectorAll('.bd-sidenav .active').forEach(function (element) {
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

  const themeButton = document.querySelector('.theme-switch-button');
  if (themeButton) {
    themeButton.addEventListener('click', function () {
      const mode = document.documentElement.getAttribute('data-mode');
      announceMessage(liveRegion, `Theme changed to ${mode}`);
    });
  }

  // Version dropdown menu is dynamically generated after page load. Listen for changes to set aria-selected
  var observer = new MutationObserver(function () {
    document.querySelectorAll('.dropdown-item').forEach(function (element) {
      if (element.classList.contains('active')) {
        element.setAttribute('aria-selected', 'true');
      }
    });
  });

  // Observe changes in the version-switcher__menu element
  var targetNode = document.querySelector('.version-switcher__menu');
  var config = { childList: true, subtree: true };

  if (targetNode) {
    observer.observe(targetNode, config);
  }
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

function createLiveRegion() {
  const liveRegion = document.createElement('div');
  liveRegion.setAttribute('role', 'status');
  liveRegion.setAttribute('aria-live', 'assertive');
  liveRegion.style.position = 'absolute';
  liveRegion.style.width = '1px';
  liveRegion.style.height = '1px';
  liveRegion.style.padding = '0';
  liveRegion.style.margin = '-1px';
  liveRegion.style.overflow = 'hidden';
  liveRegion.style.clipPath = 'inset(50%)';
  liveRegion.style.whiteSpace = 'nowrap'; `  `
  liveRegion.style.border = '0';
  document.body.appendChild(liveRegion);

  return liveRegion;
}

function announceMessage(liveRegion, message) {
  liveRegion.textContent = '';
  setTimeout(() => {
    liveRegion.textContent = message;
  }, 50);
}
