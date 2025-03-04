document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.copybtn').forEach(button => {
      console.log('Button found:', button); // Debugging: Check if buttons are found
      button.addEventListener('click', async function(event) {
          console.log('Button clicked:', button); // Debugging: Check if the click event is triggered

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
  console.log('Code block found:', codeBlock); // Debugging: Check if the code block is found

  try {
      await navigator.clipboard.writeText(codeBlock.textContent);
      console.log('Text copied to clipboard'); // Debugging: Confirm that the text is copied
  } catch (err) {
      console.error('Failed to copy text: ', err);
  }
}