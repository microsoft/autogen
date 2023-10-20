import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import ClearDBView from "./cleardb";
import FileViewer from "./fileviewer";

const ArtifactBarView = ({ setMessages, notify, skillup }: any) => {
  const [isOpen, setIsOpen] = React.useState(true);
  const minWidth = isOpen ? "330px" : "50px";

  return (
    <div
      style={{ minWidth: minWidth, maxWidth: minWidth }}
      className="transition overflow-hidden duration-300 border rounded ml-2   h-full p-2"
    >
      <div className=" gap-3">
        <div
          onClick={() => setIsOpen(!isOpen)}
          role="button"
          className=" mb-2 "
        >
          {isOpen ? (
            <>
              {" "}
              <ChevronRightIcon className="w-7 h-7 p-1 inline-block border  rounded" />{" "}
              <span className="text-xs "> close artifact bar</span>
            </>
          ) : (
            <ChevronLeftIcon className="w-7 h-7 p-1 inline-block border font-bold rounded " />
          )}
        </div>
        <div className={`${isOpen ? "" : "hidden"}`}>
          <FileViewer />
        </div>
      </div>
    </div>
  );
};

export default ArtifactBarView;
