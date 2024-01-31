import siteConfig from '@generated/docusaurus.config';
export default function prismIncludeLanguages(PrismObject) {
  const {
    themeConfig: { prism },
  } = siteConfig;
  const { additionalLanguages } = prism;
  // Prism components work on the Prism instance on the window, while prism-
  // react-renderer uses its own Prism instance. We temporarily mount the
  // instance onto window, import components to enhance it, then remove it to
  // avoid polluting global namespace.
  // You can mutate PrismObject: registering plugins, deleting languages... As
  // long as you don't re-assign it
  globalThis.Prism = PrismObject;

  additionalLanguages.forEach((lang) => {
    if (lang === 'php') {
      // eslint-disable-next-line global-require
      require('prismjs/components/prism-markup-templating.js');
    }
    // eslint-disable-next-line global-require, import/no-dynamic-require
    require(`prismjs/components/prism-${lang}`);
  });

  Prism.languages['text'] = {
    'message-id': {
      pattern: /\b(:?[A-Za-z0-9\-_]+)\s+\(:?to\s([A-Za-z0=9\-_]+)\)\:/,
      inside: {
        'class-name': /\b(?!to\b)[A-Za-z0-9\-_^]+\b/,
        punctuation: /[()]/,
        keyword: /\bto\b/
      }
    },
    builtin: /\bTERMINATE\b/,
    punctuation: /(?:(---)-+)/,
    function: />>>>>>>>.+[\r\n]?/
  };

  delete globalThis.Prism;
}
