/** @type {import('@docusaurus/types').DocusaurusConfig} */
const math = require('remark-math');
const katex = require('rehype-katex');

module.exports = {
  title: 'AutoGen',
  tagline: 'Enabling Next-Gen LLM Applications',
  url: 'https://microsoft.github.io/',
  baseUrl: '/AutoGen/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/flaml_logo.ico',
  organizationName: 'Microsoft', // Usually your GitHub org/user name.
  projectName: 'AutoGen', // Usually your repo name.
  themeConfig: {
    navbar: {
      title: 'AutoGen',
      logo: {
        alt: 'AutoGen',
        src: 'img/flaml_logo_fill.svg',
      },
      items: [
        {
          type: 'doc',
          docId: 'Getting-Started',
          position: 'left',
          label: 'Docs',
        },
        // {to: 'blog', label: 'Blog', position: 'left'},
        // {
        //   type: 'doc',
        //   docId: 'FAQ',
        //   position: 'left',
        //   label: 'FAQ',
        // },
        {
          href: 'https://github.com/microsoft/FLAML',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        // {
        //   title: 'Docs',
        //   items: [
        //     {
        //       label: 'Getting Started',
        //       to: 'docs/getting-started',
        //     },
        //   ],
        // },
        {
          title: 'Community',
          items: [
        //     // {
        //     //   label: 'Stack Overflow',
        //     //   href: 'https://stackoverflow.com/questions/tagged/pymarlin',
        //     // },
            {
              label: 'Discord',
              href: 'https://discord.gg/Cppx2vSPVP',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} AutoGen Authors. Built with Docusaurus.`,
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          editUrl:
            'https://github.com/microsoft/autogen/edit/main/website/',
          remarkPlugins: [math],
          rehypePlugins: [katex],
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
  stylesheets: [
    {
        href: "https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/katex.min.css",
        integrity: "sha384-Um5gpz1odJg5Z4HAmzPtgZKdTBHZdw8S29IecapCSB31ligYPhHQZMIlWLYQGVoc",
        crossorigin: "anonymous",
    },
  ],

  plugins: [
    // ... Your other plugins.
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        // ... Your options.
        // `hashed` is recommended as long-term-cache of index file is possible.
        hashed: true,
        blogDir:"./blog/"
        // For Docs using Chinese, The `language` is recommended to set to:
        // ```
        // language: ["en", "zh"],
        // ```
        // When applying `zh` in language, please install `nodejieba` in your project.
      },
    ],
  ],
};
