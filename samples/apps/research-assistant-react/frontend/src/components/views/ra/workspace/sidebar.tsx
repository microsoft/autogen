import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import ClearDBView from "./cleardb";

const SideBarView = ({
  setMessages,
  notify,
  skillup,
  config,
  setMetadata,
}: any) => {
  const [isOpen, setIsOpen] = React.useState(true);
  const minWidth = isOpen ? "270px" : "50px";

  return (
    <div
      style={{ minWidth: minWidth, maxWidth: minWidth }}
      className="transition overflow-hidden duration-300    h-full p-2 "
    >
      <div className="  ">
        <div
          onClick={() => setIsOpen(!isOpen)}
          role="button"
          className=" mb-2 "
        >
          {isOpen ? (
            <>
              {" "}
              <ChevronLeftIcon className="w-7 h-7   inline-block border  rounded" />{" "}
              <span className="text-xs "> close sidebar</span>
            </>
          ) : (
            <ChevronRightIcon className="w-7 h-7   inline-block border font-bold rounded " />
          )}
        </div>
        <div className="  ">
          {
            <div className={`${isOpen ? "" : "hidden"}`}>
              <ClearDBView
                notify={notify}
                setMessages={setMessages}
                skillup={skillup}
                config={config}
                setMetadata={setMetadata}
              />
            </div>
          }
        </div>
      </div>
    </div>
  );
};

export default SideBarView;
