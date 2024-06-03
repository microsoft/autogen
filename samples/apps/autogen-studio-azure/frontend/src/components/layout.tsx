import * as React from "react";
import Header from "./header";
import { appContext } from "../hooks/provider";
import Footer from "./footer";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { loginRequest } from "../authConfig";

/// import ant css
import "antd/dist/reset.css";

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
  restricted = false,
}: Props) => {

  const isAuth = useIsAuthenticated();
  const { instance, inProgress } = useMsal();
  const { user, setUser, setUserToken } = React.useContext(appContext);

  const layoutContent = (
    <div
      // style={{ height: "calc(100vh - 64px)" }}
      className={`  h-full flex flex-col`}
    >
      {showHeader && <Header meta={meta} link={link} />}
      <div className="flex-1  text-primary ">
        <title>{meta?.title + " | " + title}</title>
        <div className="   h-full  text-primary">{children}</div>
      </div>
      <Footer />
    </div>
  );

  const fetchData = async () => {
    console.log("Fetching Data for user -> " + user);
    if (!user) {
      await instance.loginRedirect(loginRequest).then((response) => {
        instance.setActiveAccount(instance.getAllAccounts()[0]);
      });
    }
  }

  const Login = () => {
    React.useEffect(() => {
      if (!isAuth && inProgress === InteractionStatus.None) {
        fetchData();
      } else {
        const account = instance.getAllAccounts()[0];
        if (account) {
          const formattedNameArr = account.name?.split(", ");
          setUser({
            name: "" + (formattedNameArr?.[1] ?? "Invalid") + " " + (formattedNameArr?.[0] ?? "User"),
            username: account.username,
            email: account.username,
            groups: account.idTokenClaims?.roles?.sort() ?? [],
          });
          setUserToken(account.idToken);
        }
      }
    }, [isAuth, inProgress, user]);

    return null;
  }

  const { darkMode } = React.useContext(appContext);
  React.useEffect(() => {
    document.getElementsByTagName("html")[0].className = `${
      darkMode === "dark" ? "dark bg-primary" : "light bg-primary"
    } `;
  }, [darkMode]);

  return (
    <appContext.Consumer>
      {(context: any) => {
        if (!isAuth) {
          return (
          <>
            <p>Authenticating....</p>
            <Login />
          </>
          );
        } else if (restricted) {
          return <div className="h-full ">{context.user && layoutContent}</div>;
        } else if(user?.groups?.length ?? 0 > 0){
          if(context.activeGroup === null){
            context.setActiveGroup(user?.groups.sort()[0])
          }
          return layoutContent;
        } else if(inProgress === InteractionStatus.None && isAuth && user?.groups?.length != 0){
          return <Login />
        } else {
          return <>Request Access for Autogen Studio.</>
        }
      }}
    </appContext.Consumer>
  );
};

export default Layout;
