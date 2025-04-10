import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import DeployManager from "../components/views/deploy/manager";
import LabsManager from "../components/views/labs/manager";

// markup
const LabsPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/labs"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <LabsManager />
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

export default LabsPage;
