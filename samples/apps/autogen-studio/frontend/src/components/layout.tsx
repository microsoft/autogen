import * as React from "react";
import Header from "./header";
import { appContext } from "../hooks/provider";
import Footer from "./footer";

/// import ant css
import "antd/dist/reset.css";

type Props = {
  title: string;
  link: string;
  children?: React.ReactNode;
  showHeader?: boolean;
  restricted?: boolean;
  meta?: any;
};

const Layout = ({
  meta,
  title,
  link,
  children,
  showHeader = true,
  restricted = false,
}: Props) => {
  const layoutContent = (
    <div
      // style={{ height: "calc(100vh - 64px)" }}
      className={`  h-full flex flex-col`}
    >
      {showHeader && <Header meta={meta} link={link} />}
      <div className="flex-1  text-primary ">
        <title>{meta?.title + " | " + title}</title>
        <div className="   h-full  text-primary">{children}</div>
      </div>
      <Footer />
    </div>
  );

  const { darkMode } = React.useContext(appContext);
  React.useEffect(() => {
    document.getElementsByTagName("html")[0].className = `${
      darkMode === "dark" ? "dark bg-primary" : "light bg-primary"
    } `;
  }, [darkMode]);

  return (
    <appContext.Consumer>
      {(context: any) => {
        if (restricted) {
          return <div className="h-full ">{context.user && layoutContent}</div>;
        } else {
          return layoutContent;
        }
      }}
    </appContext.Consumer>
  );
};

export default Layout;
