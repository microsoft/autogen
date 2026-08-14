import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import GalleryManager from "../components/views/gallery/manager";

// markup
const GalleryPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/gallery"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <GalleryManager />
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
