import React from "react";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import {
  BellIcon,
  MoonIcon,
  SunIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { ChevronDown, Menu as MenuIcon } from "lucide-react";
import { appContext } from "../hooks/provider";
import { useConfigStore } from "../hooks/store";
import { Link } from "gatsby";
import { sanitizeUrl } from "./utils/security-utils";

type ContentHeaderProps = {
  onMobileMenuToggle: () => void;
  isMobileMenuOpen: boolean;
};

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

const ContentHeader = ({
  onMobileMenuToggle,
  isMobileMenuOpen,
}: ContentHeaderProps) => {
  const { darkMode, setDarkMode, user, logout } = React.useContext(appContext);
  const { sidebar, setSidebarState, header } = useConfigStore();
  const { isExpanded } = sidebar;
  const { title, breadcrumbs } = header;

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
        {/* <div className="hidden md:block">
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
        </div> */}

        <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
          {/* Breadcrumbs */}
          <div className="flex flex-1 items-center min-w-0">
            {breadcrumbs && breadcrumbs.length > 0 ? (
              <nav aria-label="Breadcrumb" className="flex">
                <ol role="list" className="flex items-center space-x-4">
                  {breadcrumbs.map((page, index) => (
                    <li key={index}>
                      <div className="flex items-center">
                        {index > 0 && (
                          <svg
                            fill="currentColor"
                            viewBox="0 0 20 20"
                            aria-hidden="true"
                            className="size-5 shrink-0 text-secondary"
                          >
                            <path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" />
                          </svg>
                        )}
                        <Link
                          to={page.href}
                          aria-current={page.current ? "page" : undefined}
                          className={classNames(
                            "text-sm font-medium",
                            index > 0 ? "ml-4" : "",
                            page.current
                              ? "text-primary"
                              : "text-secondary hover:text-accent"
                          )}
                        >
                          {page.name}
                        </Link>
                      </div>
                    </li>
                  ))}
                </ol>
              </nav>
            ) : (
              <h1 className="text-lg font-medium text-primary">{title}</h1>
            )}
          </div>

          {/* Right side header items */}
          <div className="flex items-center gap-x-4 lg:gap-x-6 ml-auto">
            {/* Search */}
            <form className="relative flex hidden h-8">
              <label htmlFor="search-field" className="sr-only">
                Search
              </label>
              <MagnifyingGlassIcon className="pointer-events-none absolute inset-y-0 left-2 h-full w-5 text-secondary" />
              <input
                id="search-field"
                type="search"
                placeholder="Search..."
                className="block h-full w-full border-0 bg-primary py-0 pl-10 pr-0 text-primary placeholder:text-secondary focus:ring-0 sm:text-sm"
              />
            </form>

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
                <MenuButton className="flex items-center">
                  {user.avatar_url ? (
                    <img
                      className="h-8 w-8 rounded-full"
                      src={sanitizeUrl(user.avatar_url)}
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
                </MenuButton>
                <MenuItems className="absolute right-0 mt-2 w-48 origin-top-right rounded-md bg-primary py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <MenuItem>
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
                  </MenuItem>
                </MenuItems>
              </Menu>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContentHeader;
