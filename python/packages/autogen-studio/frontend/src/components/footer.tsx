import * as React from "react";
import Icon from "./icons";
import { useConfigStore } from "../hooks/store";
import { fetchVersion } from "./utils/utils";

const Footer = () => {
  const version = useConfigStore((state) => state.version);
  const setVersion = useConfigStore((state) => state.setVersion);

  React.useEffect(() => {
    if (version === null) {
      fetchVersion().then((data) => {
        if (data && data.data) {
          setVersion(data.data.version);
        }
      });
    }
  }, []);
  return (
    <div className=" text-primary p-3  border-t border-secondary flex ">
      <div className="text-xs flex-1">
        Maintained by the AI Planet Team.{" "}
        {/* <a
          target={"_blank"}
          rel={"noopener noreferrer"}
          className="underlipne inline-block border-accent border-b hover:text-accent"
          href="https://microsoft.github.io/autogen/"
        >
          {" "}
          Team.
        </a> */}
      </div>
      {version && (
        <div className="text-xs ml-2 text-secondary"> v{version}</div>
      )}
    </div>
  );
};
export default Footer;
