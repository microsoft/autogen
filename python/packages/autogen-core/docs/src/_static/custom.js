document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.copybtn').forEach(button => {
      button.addEventListener('click', async function(event) {
          // Save the current focus
          const focusedElement = document.activeElement;

          // Perform the copy action
          await copyToClipboard(this);

          // Restore the focus
          focusedElement.focus();
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