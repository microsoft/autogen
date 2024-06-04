const fixColorContrast = (selector, color) => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    elements.forEach(element => {
      element.style.color = color;
    });
  }
}

const observer = new MutationObserver(() => {
  const hashLinks = document.querySelectorAll('.hash-link[title="Direct link to heading"]');
  if (hashLinks.length > 0) {
    hashLinks.forEach(link => {
      link.setAttribute('tabindex', '-1');
    });
  }

  fixColorContrast('.token.comment', '#8a93c8')
  fixColorContrast('.token.boolean', '#ff5c79')
  fixColorContrast('blockquote a', '#0d55b4')
  fixColorContrast('.ant-select-selection-placeholder', '#747474')
});

observer.observe(document, {
  childList: true,
  subtree: true
});
