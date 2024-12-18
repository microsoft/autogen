import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import GalleryManager from "../components/views/gallery/manager";
import WebbyManager from "../components/views/webby/webby";

// markup
const GalleryPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/webby"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <WebbyManager />
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

export default GalleryPage;
