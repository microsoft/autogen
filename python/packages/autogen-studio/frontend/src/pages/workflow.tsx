import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import { FoundryManager } from "../components/views/workflows";

// markup
const WorkflowPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/workflow"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <FoundryManager />
      </main>
    </Layout>
  );
};

export const query = graphql`
  query HomePageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default WorkflowPage;
