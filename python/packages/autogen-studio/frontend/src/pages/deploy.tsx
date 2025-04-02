import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import DeployManager from "../components/views/deploy/manager";

// markup
const DeployPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/deploy"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <DeployManager />
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

export default DeployPage;
