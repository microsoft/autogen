import {
  ChevronDownIcon,
  ChevronUpIcon,
  Cog8ToothIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import React, { ReactChildren, ReactChild, useRef } from "react";
import Icon from "./icons";

interface IProps {
  children?: ReactChild | ReactChildren;
  title?: string | ReactChild;
  subtitle?: string | ReactChild | ReactChildren;
  count?: number;
  active?: boolean;
  cursor?: string;
  icon?: ReactChild;
  padding?: string;
  className?: string;
  open?: boolean;
  hoverable?: boolean;
  onClick?: () => void;
}

export const SectionHeader = ({
  children,
  title,
  subtitle,
  count,
  icon,
}: IProps) => {
  return (
    <div className="mb-4">
      <h1 className="text-primary text-2xl">
        {/* {count !== null && <span className="text-accent mr-1">{count}</span>} */}
        {icon && <>{icon}</>}
        {title}
        {count !== null && (
          <span className="text-accent mr-1 ml-2 text-xs">{count}</span>
        )}
      </h1>
      {subtitle && <span className="inline-block">{subtitle}</span>}
      {children}
    </div>
  );
};

export const IconButton = ({
  onClick,
  icon,
  className,
  active = false,
}: IProps) => {
  return (
    <span
      role={"button"}
      onClick={onClick}
      className={`inline-block mr-2 hover:text-accent transition duration-300 ${className} ${
        active ? "border-accent border rounded text-accent" : ""
      }`}
    >
      {icon}
    </span>
  );
};

export const LaunchButton = ({ children, onClick }: any) => {
  return (
    <button
      role={"button"}
      className={`    focus:ring ring-accent  ring-l-none  p-3 px-5 rounded  cursor-pointer hover:brightness-110 bg-accent transition duration-500    text-white`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

export const SecondaryButton = ({ children, onClick, className }: any) => {
  return (
    <button
      role={"button"}
      className={` ${className}   focus:ring ring-accent  p-2 px-5 rounded  cursor-pointer hover:brightness-90 bg-secondary transition duration-500    text-primary`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

export const Card = ({
  children,
  title,
  subtitle,
  hoverable = true,
  active,
  cursor = "cursor-pointer",
  className = "p-3",
  onClick,
}: IProps) => {
  let border = active
    ? "border-accent"
    : "border-secondary hover:border-accent ";
  border = hoverable ? border : "border-secondary";

  return (
    <div
      onClick={onClick}
      role={"button"}
      className={`${border} border-2 bg-secondary  group ${className} rounded ${cursor} transition duration-300`}
    >
      <div className="mt- text-sm text-secondary  break-words">
        {title && (
          <div className="text-accent rounded font-semibold  text-xs pb-1">
            {title}
          </div>
        )}
        <div>{subtitle}</div>
      </div>
    </div>
  );
};

export const CollapseBox = ({
  title,
  subtitle,
  children,
  className = " p-3",
  open = false,
}: IProps) => {
  const [isOpen, setIsOpen] = React.useState<boolean>(open);
  const chevronClass = "h-4 cursor-pointer inline-block mr-1";
  return (
    <div
      onMouseDown={(e) => {
        if (e.detail > 1) {
          e.preventDefault();
        }
      }}
      className="bordper border-secondary rounded"
    >
      <div
        onClick={() => {
          setIsOpen(!isOpen);
        }}
        className={`cursor-pointer bg-secondary p-2 rounded ${
          isOpen ? "rounded-b-none " : " "
        }"}`}
      >
        {isOpen && <ChevronUpIcon className={chevronClass} />}
        {!isOpen && <ChevronDownIcon className={chevronClass} />}

        <span className=" inline-block -mt-2 mb-2 text-xs">
          {" "}
          {/* {isOpen ? "hide" : "show"} section |  */}
          {title}
        </span>
      </div>

      {isOpen && (
        <div className={`${className} bg-light  rounded rounded-t-none`}>
          {children}
        </div>
      )}
    </div>
  );
};

export const HighLight = ({ children }: IProps) => {
  return <span className="border-b border-accent">{children}</span>;
};

export const LoadBox = ({
  subtitle,
  className = "my-2 text-accent ",
}: IProps) => {
  return (
    <div className={`${className} `}>
      {" "}
      <span className="mr-2 ">
        {" "}
        <Icon size={5} icon="loading" />
      </span>{" "}
      {subtitle}
    </div>
  );
};

export const LoadingBar = ({ children }: IProps) => {
  return (
    <>
      <div className="rounded bg-secondary mt-4 p-3">
        <span className="inline-block h-6 w-6 relative mr-2">
          <Cog8ToothIcon className="animate-ping text-accent absolute inline-flex h-full w-full rounded-ful  opacity-75" />
          <Cog8ToothIcon className="relative text-accent animate-spin  inline-flex rounded-full h-6 w-6" />
        </span>
        {children}
      </div>
      <div className="relative">
        <div className="loadbar rounded-b"></div>
      </div>
    </>
  );
};

export const MessageBox = ({ title, children, className }: IProps) => {
  const messageBox = useRef(null);

  const closeMessage = () => {
    messageBox.current.remove();
  };

  return (
    <div
      ref={messageBox}
      className={`${className} p-3  rounded  bg-secondary transition duration-1000 ease-in-out  overflow-hidden`}
    >
      {" "}
      <div className="flex gap-2 mb-2">
        <div className="flex-1">
          {/* <span className="mr-2 text-accent">
            <InformationCircleIcon className="h-6 w-6 inline-block" />
          </span>{" "} */}
          <span className="font-semibold text-primary text-base">{title}</span>
        </div>
        <div>
          <span
            onClick={() => {
              closeMessage();
            }}
            className=" border border-secondary bg-secondary brightness-125 hover:brightness-100 cursor-pointer transition duration-200   inline-block px-1 pb-1 rounded text-primary"
          >
            <XMarkIcon className="h-4 w-4 inline-block" />
          </span>
        </div>
      </div>
      {children}
    </div>
  );
};
