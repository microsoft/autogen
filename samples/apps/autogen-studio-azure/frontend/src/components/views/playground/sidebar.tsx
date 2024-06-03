import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import SessionsView from "./sessions";

const SideBarView = () => {
  const [isOpen, setIsOpen] = React.useState(true);
  const minWidth = isOpen ? "270px" : "50px";

  let windowHeight, sidebarMaxHeight;
  if (typeof window !== "undefined") {
    windowHeight = window.innerHeight;
    sidebarMaxHeight = windowHeight - 180 + "px";
  }

  return (
    <div
      style={{
        minWidth: minWidth,
        maxWidth: minWidth,
        height: "calc(100vh - 190px)",
      }}
      className="    "
    >
      <div className=" transition overflow-hidden duration-300  flex flex-col   h-full p-2 overflow-y-scroll scroll rounded ">
        <div className={`${isOpen ? "" : "hidden"}  `}>
          {/* <AgentsView /> */}
          {<SessionsView />}
        </div>
      </div>
      <div
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        className=" hover:text-accent duration-150  "
      >
        {isOpen ? (
          <div className="mt-4  ">
            {" "}
            <ChevronLeftIcon className="w-6 h-6  inline-block    rounded" />{" "}
            <span className="text-xs "> close sidebar</span>
          </div>
        ) : (
          <ChevronRightIcon className="w-6 h-6   inline-block   font-bold rounded " />
        )}
      </div>
    </div>
  );
};

export default SideBarView;
