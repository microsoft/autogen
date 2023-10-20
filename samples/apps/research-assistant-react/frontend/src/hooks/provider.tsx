import React, { useState } from "react";
import {
  eraseCookie,
  getLocalStorage,
  setLocalStorage,
} from "../components/utils";

export interface IUser {
  name: string;
  email?: string;
  username?: string;
  avatar_url?: string;
  metadata?: any;
}

export interface AppContextType {
  user: IUser | null;
  setUser: any;
  logout: any;
  cookie_name: string;
  darkMode: string;
  setDarkMode: any;
}

const cookie_name = "coral_app_cookie_";

export const appContext = React.createContext<AppContextType>(
  {} as AppContextType
);
const Provider = ({ children }: any) => {
  const [darkMode, setDarkMode] = useState(
    getLocalStorage("darkmode", false) === null
      ? "dark"
      : getLocalStorage("darkmode", false) !== ("dark" || "light")
      ? getLocalStorage("darkmode", false)
      : "light"
  );

  const logout = () => {
    setUser(null);
    eraseCookie(cookie_name);
  };

  const updateDarkMode = (darkMode: string) => {
    setDarkMode(darkMode);
    setLocalStorage("darkmode", darkMode, false);
  };

  const [user, setUser] = useState<IUser | null>(null);

  return (
    <appContext.Provider
      value={{
        user,
        setUser,
        logout,
        cookie_name,
        darkMode,
        setDarkMode: updateDarkMode,
      }}
    >
      {children}
    </appContext.Provider>
  );
};

export default ({ element }: any) => <Provider>{element}</Provider>;
