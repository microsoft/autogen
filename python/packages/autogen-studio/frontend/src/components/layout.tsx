import * as React from "react";
import { Dialog } from "@headlessui/react";
import { X } from "lucide-react";
import { appContext } from "../hooks/provider";
import { useConfigStore } from "../hooks/store";
import Footer from "./footer";
import "antd/dist/reset.css";
import SideBar from "./sidebar";
import ContentHeader from "./contentheader";
import { ConfigProvider, theme } from "antd";
import { useAuth } from "../auth/context";
import ProtectedRoute from "../auth/protected";

const classNames = (...classes: (string | undefined | boolean)[]) => {
  return classes.filter(Boolean).join(" ");
};

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
  restricted = true, // Default to restricted for security
}: Props) => {
  const { darkMode } = React.useContext(appContext);
  const { sidebar } = useConfigStore();
  const { isExpanded } = sidebar;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);
  const { authType } = useAuth();

  // Close mobile menu on route change
  React.useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [link]);

  React.useEffect(() => {
    document.getElementsByTagName("html")[0].className = `${
      darkMode === "dark" ? "dark bg-primary" : "light bg-primary"
    }`;
  }, [darkMode]);

  const layoutContent = (
    <div className="min-h-screen flex">
      {/* Mobile menu */}
      <Dialog
        as="div"
        open={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
        className="relative z-50 md:hidden"
      >
        {/* Backdrop */}
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

        {/* Mobile Sidebar Container */}
        <div className="fixed inset-0 flex">
          <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
            <div className="absolute right-0 top-0 flex w-16 justify-center pt-5">
              <button
                type="button"
                className="text-secondary"
                onClick={() => setIsMobileMenuOpen(false)}
              >
                <span className="sr-only">Close sidebar</span>
                <X className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            <SideBar link={link} meta={meta} isMobile={true} />
          </Dialog.Panel>
        </div>
      </Dialog>

      {/* Desktop sidebar */}
      <div className="hidden md:flex md:flex-col md:fixed md:inset-y-0">
        <SideBar link={link} meta={meta} isMobile={false} />
      </div>

      {/* Content area */}
      <div
        className={classNames(
          "flex-1 flex flex-col min-h-screen",
          "transition-all duration-300 ease-in-out",
          "md:pl-16",
          isExpanded ? "md:pl-72" : "md:pl-16"
        )}
      >
        {showHeader && (
          <ContentHeader
            isMobileMenuOpen={isMobileMenuOpen}
            onMobileMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          />
        )}

        <ConfigProvider
          theme={{
            token: {
              borderRadius: 4,
              colorBgBase: darkMode === "dark" ? "#05080C" : "#ffffff",
            },
            algorithm:
              darkMode === "dark"
                ? theme.darkAlgorithm
                : theme.defaultAlgorithm,
          }}
        >
          <main className="flex-1 p-2 text-primary">{children}</main>
        </ConfigProvider>

        <Footer />
      </div>
    </div>
  );

  // If page is restricted and auth is not 'none', wrap with ProtectedRoute
  if (restricted && authType !== "none") {
    return <ProtectedRoute>{layoutContent}</ProtectedRoute>;
  }

  // Otherwise, render without protection
  return layoutContent;
};

export default Layout;

// Lite Layout Component for simplified lite mode
type LiteLayoutProps = {
  children?: React.ReactNode;
  showHeader?: boolean;
  showFooter?: boolean;
  restricted?: boolean;
};

export const LiteLayout = ({
  children,
  showHeader = true,
  showFooter = true,
  restricted = true,
}: LiteLayoutProps) => {
  const { darkMode } = React.useContext(appContext);
  const { authType } = useAuth();
  const { setHeader } = useConfigStore();

  React.useEffect(() => {
    document.getElementsByTagName("html")[0].className = `${
      darkMode === "dark" ? "dark bg-primary" : "light bg-primary"
    }`;
  }, [darkMode]);

  // Set up lite mode breadcrumbs and header
  React.useEffect(() => {
    setHeader({
      title: "AutoGen Studio Lite",
      breadcrumbs: [
        {
          name: "Home",
          href: "/",
          current: false,
        },
        {
          name: "Lite Mode",
          href: "/lite",
          current: true,
        },
      ],
    });
  }, [setHeader]);

  const layoutContent = (
    <div className="min-h-screen flex flex-col">
      {showHeader && (
        <ContentHeader
          isMobileMenuOpen={false}
          onMobileMenuToggle={() => {}} // No mobile menu in lite mode
        />
      )}

      <ConfigProvider
        theme={{
          token: {
            borderRadius: 4,
            colorBgBase: darkMode === "dark" ? "#05080C" : "#ffffff",
          },
          algorithm:
            darkMode === "dark" ? theme.darkAlgorithm : theme.defaultAlgorithm,
        }}
      >
        <main className="flex-1 p-2 text-primary">{children}</main>
      </ConfigProvider>

      {showFooter && <Footer />}
    </div>
  );

  // If page is restricted and auth is not 'none', wrap with ProtectedRoute
  if (restricted && authType !== "none") {
    return <ProtectedRoute>{layoutContent}</ProtectedRoute>;
  }

  // Otherwise, render without protection
  return layoutContent;
};
