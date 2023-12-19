/** @type {import('@docusaurus/types').DocusaurusConfig} */
const math = require("remark-math");
const katex = require("rehype-katex");

module.exports = {
  title: "AutoGen",
  tagline: "Enable Next-Gen Large Language Model Applications",
  url: "https://microsoft.github.io",
  baseUrl: "/autogen/",
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",
  favicon: "img/ag.ico",
  organizationName: "Microsoft", // Usually your GitHub org/user name.
  projectName: "AutoGen", // Usually your repo name.
  themeConfig: {
    navbar: {
      title: "AutoGen",
      logo: {
        alt: "AutoGen",
        src: "img/ag.svg",
      },
      items: [
        {
          type: "doc",
          docId: "Getting-Started",
          position: "left",
          label: "Docs",
        },
        {
          type: "doc",
          docId: "reference/agentchat/conversable_agent",
          position: "left",
          label: "SDK",
        },
        { to: "blog", label: "Blog", position: "left" },
        {
          type: "doc",
          docId: "FAQ",
          position: "left",
          label: "FAQ",
        },
        {
          href: "https://github.com/microsoft/autogen",
          label: "GitHub",
          position: "right",
        },
        // {
        //   to: 'examples',
        //   label: 'Examples',
        // },
        {
          type: "doc",
          docId: "Examples",
          position: "left",
          label: "Examples",
        },
        {
          label: "Resources",
          type: "dropdown",
          items: [
            {
              type: "doc",
              docId: "Ecosystem",
            },
            {
              type: "doc",
              docId: "Gallery",
            },
          ],
        },
      ],
    },
    footer: {
      style: "dark",
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
          title: "Community",
          items: [
            //     // {
            //     //   label: 'Stack Overflow',
            //     //   href: 'https://stackoverflow.com/questions/tagged/pymarlin',
            //     // },
            {
              label: "Discord",
              href: "https://discord.gg/pAbnFJrkgZ",
            },
            {
              label: "Twitter",
              href: "https://twitter.com/pyautogen",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} AutoGen Authors |  <a target="_blank" href="https://go.microsoft.com/fwlink/?LinkId=521839">Privacy and Cookies</a>`,
    },
  },
  presets: [
    [
      "@docusaurus/preset-classic",
      {
        blog: {
          showReadingTime: true,
          blogSidebarCount: "ALL",
          // Adjust any other blog settings as needed
        },
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          // Please change this to your repo.
          editUrl: "https://github.com/microsoft/autogen/edit/main/website/",
          remarkPlugins: [math],
          rehypePlugins: [katex],
        },
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      },
    ],
  ],
  stylesheets: [
    {
      href: "https://cdn.jsdelivr.net/npm/katex@0.13.11/dist/katex.min.css",
      integrity:
        "sha384-Um5gpz1odJg5Z4HAmzPtgZKdTBHZdw8S29IecapCSB31ligYPhHQZMIlWLYQGVoc",
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
        blogDir: "./blog/",
        // For Docs using Chinese, The `language` is recommended to set to:
        // ```
        // language: ["en", "zh"],
        // ```
        // When applying `zh` in language, please install `nodejieba` in your project.
      },
    ],
  ],
};
