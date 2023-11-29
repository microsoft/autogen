import * as React from "react";
import { graphql } from "gatsby";
import Layout from "../../components/layout";
import GalleryView from "../../components/views/gallery/gallery";

// markup
const GalleryPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Gallery" link={"/gallery"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <GalleryView />
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
