import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import SkillsView from "./skills";
import AgentsView from "./agents";

const SideBarView = ({ setMessages, notify, skillup, config }: any) => {
  const [isOpen, setIsOpen] = React.useState(true);
  const minWidth = isOpen ? "270px" : "50px";

  return (
    <div
      style={{ minWidth: minWidth, maxWidth: minWidth }}
      className="transition overflow-hidden duration-300  flex flex-col    h-full p-2 "
    >
      <div className="flex-1 ">
        <div className={`${isOpen ? "" : "hidden"}`}>
          <AgentsView />
          <SkillsView
            notify={notify}
            setMessages={setMessages}
            skillup={skillup}
            config={config}
          />
        </div>
      </div>
      <div
        onClick={() => setIsOpen(!isOpen)}
        role="button"
        className=" hover:text-accent duration-150  "
      >
        {isOpen ? (
          <>
            {" "}
            <ChevronLeftIcon className="w-6 h-6  inline-block    rounded" />{" "}
            <span className="text-xs "> close sidebar</span>
          </>
        ) : (
          <ChevronRightIcon className="w-6 h-6   inline-block   font-bold rounded " />
        )}
      </div>
    </div>
  );
};

export default SideBarView;
