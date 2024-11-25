import * as React from "react";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import { TriangleAlertIcon } from "lucide-react";

// markup
const SettingsPage = ({ data }: any) => {
  return (
    <Layout meta={data.site.siteMetadata} title="Home" link={"/build"}>
      <main style={{ height: "100%" }} className=" h-full ">
        <div className="mb-2"> Settings</div>
        <div className="p-2 mt-4 bg-tertiary rounded ">
          <TriangleAlertIcon
            className="w-5 h-5 text-primary inline-block -mt-1"
            strokeWidth={1.5}
          />{" "}
          Work in progress ..
        </div>
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

export default SettingsPage;
