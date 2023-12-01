import * as React from "react";
import { graphql } from "gatsby";
import Layout from "../../components/layout";
import GalleryView from "../../components/views/gallery/gallery";
import GalleryDetailView from "../../components/views/gallery/viewer";

// markup
const GalleryViewer = ({ location, data }: any) => {
  console.log("location", location);
  return (
    <Layout meta={data.site.siteMetadata} title="Gallery" link={"/gallery"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <GalleryDetailView location={location} />
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

export default GalleryViewer;
