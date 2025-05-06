import type { GatsbyConfig } from "gatsby";
import fs from "fs";

const envFile = `.env.${process.env.NODE_ENV}`;

fs.access(envFile, fs.constants.F_OK, (err) => {
  if (err) {
    console.warn(`File '${envFile}' is missing. Using default values.`);
  }
});

require("dotenv").config({
  path: envFile,
});

const TITLE = process.env.GATSBY_SITE_TITLE   || "AI Planet Studio";
const DESC  = process.env.GATSBY_SITE_DESC    || "Build Multi-Agent Workflows & Apps";

const config: GatsbyConfig = {
  pathPrefix: process.env.PREFIX_PATH_VALUE || "",
  siteMetadata: {
    title: TITLE,
    description: DESC,
    siteUrl: `http://tbd.place`,
  },
  // More easily incorporate content into your pages through automatic TypeScript type generation and better GraphQL IntelliSense.
  // If you use VSCode you can also use the GraphQL plugin
  // Learn more at: https://gatsby.dev/graphql-typegen
  graphqlTypegen: true,
  plugins: [
    "gatsby-plugin-postcss",
    "gatsby-plugin-image",
    "gatsby-plugin-sitemap",
    {
      resolve: "gatsby-plugin-manifest",
      options: {
        icon: "src/images/icon.png",
      },
    },
    "gatsby-plugin-mdx",
    "gatsby-plugin-sharp",
    "gatsby-transformer-sharp",
    {
      resolve: "gatsby-source-filesystem",
      options: {
        name: "images",
        path: "./src/images/",
      },
      __key: "images",
    },
    {
      resolve: "gatsby-source-filesystem",
      options: {
        name: "pages",
        path: "./src/pages/",
      },
      __key: "pages",
    },
  ],
};

export default config;
