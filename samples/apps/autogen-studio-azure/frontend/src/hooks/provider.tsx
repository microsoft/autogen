import React, { useState } from "react";
import {
  eraseCookie,
  getLocalStorage,
  setLocalStorage,
} from "../components/utils";
import { message } from "antd";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig } from '../authConfig';

export interface IUser {
  name: string;
  groups: string[];
  email?: string;
  username?: string;
  avatar_url?: string;
  metadata?: any;
}

export interface AppContextType {
  user: IUser | null;
  setUser: any;
  userToken: string | null;
  setUserToken: any;
  logout: any;
  cookie_name: string;
  darkMode: string;
  setDarkMode: any;
  activeGroup: string | null;
  setActiveGroup: any;
}

const cookie_name = "coral_app_cookie_";
const msalInstance = new PublicClientApplication(msalConfig);

export const appContext = React.createContext<AppContextType>(
  {} as AppContextType
);
const Provider = ({ children }: any) => {
  const storedValueDarkMode = getLocalStorage("darkmode", false);
  const storedValueActiveGroup = getLocalStorage("activeGroup", false);

  const [darkMode, setDarkMode] = useState(
    storedValueDarkMode === null ? "light" : storedValueDarkMode === "dark" ? "dark" : "light"
  );

  const [activeGroup, setActiveGroup] = useState(
    storedValueActiveGroup === null ? null : storedValueActiveGroup
  );

  const [user, setUser] = useState<IUser | null>(null);
  const [userToken, setUserToken] = useState<string | null>(null);

  const logout = async () => {
    message.warning("Logging out... ");
    await new Promise(f => setTimeout(f, 3000));
    setUser(null);
    msalInstance.logoutRedirect();
  };

  const updateDarkMode = (darkMode: string) => {
    setDarkMode(darkMode);
    setLocalStorage("darkmode", darkMode, false);
  };


  const updateActiveGroup = (newGroup: string) => {
    setActiveGroup(newGroup);
    setLocalStorage("activeGroup", newGroup, false);
  };


  return (
    <MsalProvider instance={msalInstance}>
      <appContext.Provider
          value={{
            user,
            setUser,
            logout,
            cookie_name,
            userToken,
            setUserToken,
            darkMode,
            setDarkMode: updateDarkMode,
            activeGroup,
            setActiveGroup: updateActiveGroup,
          }}
        >
          {children}
        </appContext.Provider>
      </MsalProvider>
  );
};

export default ({ element }: any) => <Provider>{element}</Provider>;
