import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import McpManager from "../components/views/mcp/manager";

// markup
const McpPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="MCP Playground" link={"/mcp"}>
      <main style={{ height: "100%" }} className="h-full">
        <McpManager />
      </main>
    </Layout>
  );
};

export const query = graphql`
  query McpPageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default McpPage;
