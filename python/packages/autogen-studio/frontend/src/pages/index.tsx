import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import ChatView from "../components/views/session/chat/chat";
import { SessionManager } from "../components/views/session/manager";

// markup
const IndexPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <SessionManager />
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
