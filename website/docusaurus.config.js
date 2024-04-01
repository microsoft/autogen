/** @type {import('@docusaurus/types').DocusaurusConfig} */
const math = require("remark-math");
const katex = require("rehype-katex");

customPostCssPlugin = () => {
  return {
    name: "custom-postcss",
    configurePostCss(options) {
      options.plugins.push(require("postcss-preset-env"));
      return options;
    }
  };
}

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
  scripts: [
    {
      src: '/autogen/js/custom.js',
      async: true,
      defer: true,
    },
  ],
  markdown: {
    format: 'detect', // Support for MD files with .md extension
  },
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
          label: "API",
        },
        { to: "blog", label: "Blog", position: "left" },
        {
          type: "doc",
          docId: "FAQ",
          position: "left",
          label: "FAQ",
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
          to: "docs/notebooks",
          position: "left",
          label: "Notebooks",
        },
        {
          type: "doc",
          position: "left",
          docId: "Gallery",
        },
        {
          label: "Other Languages",
          type: "dropdown",
          position: "right",
          items: [
            {
              label: "Dotnet",
              href: "https://microsoft.github.io/autogen-for-net/",
            }
          ],
        },
        {
          href: "https://github.com/microsoft/autogen",
          label: "GitHub",
          position: "right",
        }
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
      copyright: `Copyright © ${new Date().getFullYear()} AutoGen Authors |  <a target="_blank" style="color:#10adff" href="https://go.microsoft.com/fwlink/?LinkId=521839">Privacy and Cookies</a>`,
    },
    announcementBar: {
      id: 'whats_new',
      content:
        'What\'s new in AutoGen? Read <a href="/autogen/blog/2024/03/03/AutoGen-Update">this blog</a> for an overview of updates',
      backgroundColor: '#fafbfc',
      textColor: '#091E42',
      isCloseable: true,
    },
    /* Clarity Config */
    clarity: {
      ID: "lnxpe6skj1", // The Tracking ID provided by Clarity
    }
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
    customPostCssPlugin,
    [
      "@docusaurus/plugin-client-redirects",
      {
        redirects: [
          {
            to: "/docs/topics/llm_configuration",
            from: ["/docs/llm_endpoint_configuration/"],
          },
          {
            to: "/docs/ecosystem/memgpt/",
            from: ["/docs/Ecosystem"],
          },
          {
            to: "/docs/Getting-Started",
            from: ["/docs/"],
          },
          {
            to: "/docs/topics/llm_configuration",
            from: ["/docs/llm_configuration"],
          },
          {
            to: "/docs/tutorial/chat-termination",
            from: ["/docs/tutorial/termination"],
          },
          {
            to: "/docs/tutorial/what-next",
            from: ["/docs/tutorial/what-is-next"],
          },
          {
            to: "/docs/topics/non-openai-models/local-lm-studio",
            from: ["/docs/topics/non-openai-models/lm-studio"],
          },
          {
            to: "/docs/notebooks/agentchat_nested_chats_chess",
            from: ["/docs/notebooks/agentchat_chess"],
          }
        ],
      },
    ],
    [
      'docusaurus-plugin-clarity',
      {
      }
    ],
  ],
};
