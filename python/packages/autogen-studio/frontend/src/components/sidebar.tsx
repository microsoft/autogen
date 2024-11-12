import React from "react";
import { Link } from "gatsby";
import { useConfigStore } from "../hooks/store";
import { Tooltip } from "antd";
import { Blocks, Settings, MessagesSquare } from "lucide-react";
import Icon from "./icons";

const navigation = [
  // { name: "Build", href: "/build", icon: Blocks },
  { name: "Playground", href: "/", icon: MessagesSquare },
];

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

type SidebarProps = {
  link: string;
  meta?: {
    title: string;
    description: string;
  };
  isMobile: boolean;
};

const Sidebar = ({ link, meta, isMobile }: SidebarProps) => {
  const { sidebar } = useConfigStore();
  const { isExpanded } = sidebar;

  // Always show full sidebar in mobile view
  const showFull = isMobile || isExpanded;

  return (
    <div
      className={classNames(
        "flex grow flex-col gap-y-5 overflow-y-auto border-r border-secondary bg-primary",
        "transition-all duration-300 ease-in-out",
        showFull ? "w-72 px-6" : "w-16 px-2"
      )}
    >
      {/* App Logo/Title */}
      <div
        className={`flex h-16 items-center ${showFull ? "gap-x-3" : "ml-2"}`}
      >
        <div className="w-8 text-right text-accent">
          <Icon icon="app" size={8} />
        </div>
        {showFull && (
          <div className="flex flex-col" style={{ minWidth: "200px" }}>
            <span className="text-base font-semibold text-primary">
              {meta?.title}
            </span>
            <span className="text-xs text-secondary">{meta?.description}</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col">
        <ul role="list" className="flex flex-1 flex-col gap-y-7">
          {/* Main Navigation */}
          <li>
            <ul
              role="list"
              className={classNames(
                "-mx-2 space-y-1",
                !showFull && "items-center"
              )}
            >
              {navigation.map((item) => {
                const isActive = item.href === link;
                const IconComponent = item.icon;

                const navLink = (
                  <Link
                    to={item.href}
                    className={classNames(
                      isActive
                        ? "text-accent"
                        : "text-primary hover:text-accent hover:bg-secondary",
                      "group flex gap-x-3 rounded-md p-2 text-sm font-medium",
                      !showFull && "justify-center"
                    )}
                  >
                    <IconComponent
                      className={classNames(
                        isActive
                          ? "text-accent"
                          : "text-secondary group-hover:text-accent",
                        "h-6 w-6 shrink-0"
                      )}
                    />
                    {showFull && item.name}
                  </Link>
                );

                return (
                  <li key={item.name}>
                    {!showFull && !isMobile ? (
                      <Tooltip title={item.name} placement="right">
                        {navLink}
                      </Tooltip>
                    ) : (
                      navLink
                    )}
                  </li>
                );
              })}
            </ul>
          </li>

          {/* Settings at bottom */}
          <li
            className={classNames(
              "mt-auto -mx-2 mb-4",
              !showFull && "flex justify-center"
            )}
          >
            {!showFull && !isMobile ? (
              <Tooltip title="Settings" placement="right">
                <Link
                  to="/settings"
                  className={classNames(
                    "group flex gap-x-3 rounded-md p-2 text-sm font-medium",
                    "text-primary hover:text-accent hover:bg-secondary",
                    !showFull && "justify-center"
                  )}
                >
                  <Settings className="h-6 w-6 shrink-0 text-secondary group-hover:text-accent" />
                </Link>
              </Tooltip>
            ) : (
              <Link
                to="/settings"
                className="group flex gap-x-3 rounded-md p-2 text-sm font-medium text-primary hover:text-accent hover:bg-secondary"
              >
                <Settings className="h-6 w-6 shrink-0 text-secondary group-hover:text-accent" />
                {showFull && "Settings"}
              </Link>
            )}
          </li>
        </ul>
      </nav>
    </div>
  );
};

export default Sidebar;
