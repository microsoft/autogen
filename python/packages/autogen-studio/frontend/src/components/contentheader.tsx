import React from "react";
import { Menu } from "@headlessui/react";
import {
  BellIcon,
  MoonIcon,
  SunIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import {
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Menu as MenuIcon,
} from "lucide-react";
import { Tooltip } from "antd";
import { appContext } from "../hooks/provider";
import { useConfigStore } from "../hooks/store";

type ContentHeaderProps = {
  title?: string;
  onMobileMenuToggle: () => void;
  isMobileMenuOpen: boolean;
};

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

const ContentHeader = ({
  title,
  onMobileMenuToggle,
  isMobileMenuOpen,
}: ContentHeaderProps) => {
  const { darkMode, setDarkMode, user, logout } = React.useContext(appContext);
  const { sidebar, setSidebarState } = useConfigStore();
  const { isExpanded } = sidebar;

  return (
    <div className="sticky top-0 z-40 bg-primary border-b border-secondary">
      <div className="flex h-16 items-center gap-x-4 px-4">
        {/* Mobile Menu Button */}
        <button
          onClick={onMobileMenuToggle}
          className="md:hidden p-2 rounded-md hover:bg-secondary text-secondary hover:text-accent transition-colors"
          aria-label="Toggle mobile menu"
        >
          <MenuIcon className="h-6 w-6" />
        </button>

        {/* Desktop Sidebar Toggle - Hidden on Mobile */}
        <div className="hidden md:block">
          <Tooltip title={isExpanded ? "Close Sidebar" : "Open Sidebar"}>
            <button
              onClick={() => setSidebarState({ isExpanded: !isExpanded })}
              className={classNames(
                "p-2 rounded-md hover:bg-secondary",
                "hover:text-accent text-secondary transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
              )}
            >
              {isExpanded ? (
                <PanelLeftClose strokeWidth={1.5} className="h-6 w-6" />
              ) : (
                <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
              )}
            </button>
          </Tooltip>
        </div>

        <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
          {/* Search */}
          <div className="flex flex-1 items-center">
            <form className="hidden relative flex flex-1">
              <label htmlFor="search-field" className="sr-only">
                Search
              </label>
              <MagnifyingGlassIcon className="pointer-events-none absolute inset-y-0 left-0 h-full w-5 text-secondary" />
              <input
                id="search-field"
                type="search"
                placeholder="Search..."
                className="block h-full w-full border-0 bg-primary py-0 pl-8 pr-0 text-primary placeholder:text-secondary focus:ring-0 sm:text-sm"
              />
            </form>
          </div>

          {/* Right side header items */}
          <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
            {/* Dark Mode Toggle */}
            <button
              onClick={() =>
                setDarkMode(darkMode === "dark" ? "light" : "dark")
              }
              className="text-secondary hover:text-primary"
            >
              {darkMode === "dark" ? (
                <MoonIcon className="h-6 w-6" />
              ) : (
                <SunIcon className="h-6 w-6" />
              )}
            </button>

            {/* Notifications */}
            <button className="text-secondary hidden hover:text-primary">
              <BellIcon className="h-6 w-6" />
            </button>

            {/* Separator */}
            <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-secondary" />

            {/* User Menu */}
            {user && (
              <Menu as="div" className="relative">
                <Menu.Button className="flex items-center">
                  {user.avatar_url ? (
                    <img
                      className="h-8 w-8 rounded-full"
                      src={user.avatar_url}
                      alt={user.name}
                    />
                  ) : (
                    <div className="border-2 bg-accent h-8 w-8 rounded-full flex items-center justify-center text-white">
                      {user.name?.[0]}
                    </div>
                  )}
                  <span className="hidden lg:flex lg:items-center">
                    <span className="ml-4 text-sm text-primary">
                      {user.name}
                    </span>
                    <ChevronDown className="ml-2 h-5 w-5 text-secondary" />
                  </span>
                </Menu.Button>
                <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-md bg-primary py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <Menu.Item>
                    {({ active }) => (
                      <a
                        href="#"
                        onClick={() => logout()}
                        className={`${
                          active ? "bg-secondary" : ""
                        } block px-4 py-2 text-sm text-primary`}
                      >
                        Sign out
                      </a>
                    )}
                  </Menu.Item>
                </Menu.Items>
              </Menu>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContentHeader;
