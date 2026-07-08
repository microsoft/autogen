import * as React from "react";
import { graphql } from "gatsby";

import { SessionManager } from "../components/views/playground/manager";
import { LiteLayout } from "../components/layout";

// markup
const LitePage = ({ data }: any) => {
  return (
    <LiteLayout>
      <main style={{ height: "100%" }} className="h-full">
        <SessionManager />
      </main>
    </LiteLayout>
  );
};

export const query = graphql`
  query LitePageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default LitePage;

export const Head = () => (
  <>
    <title>AutoGen Studio - Lite Mode</title>
    <meta
      name="description"
      content="AutoGen Studio Lite Mode - Simplified chat interface"
    />
  </>
);
