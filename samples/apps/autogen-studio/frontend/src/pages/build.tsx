import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import BuildView from "../components/views/builder/build";

// markup
const IndexPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/build"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <BuildView />
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

export default IndexPage;
