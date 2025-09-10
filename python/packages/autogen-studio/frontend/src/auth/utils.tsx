import React from "react";
import { GithubOutlined, WindowsOutlined } from "@ant-design/icons";

export interface AuthProviderInfo {
  name: string;
  displayName: string;
  icon: React.ReactNode;
  color: string;
  connectingText: string;
  buttonText: string;
}

export const getAuthProviderInfo = (authType: string): AuthProviderInfo => {
  switch (authType) {
    case "github":
      return {
        name: "github",
        displayName: "GitHub",
        icon: <GithubOutlined />,
        color: "#24292f",
        connectingText: "Connecting to GitHub...",
        buttonText: "Sign in with GitHub",
      };
    
    case "msal":
      return {
        name: "msal",
        displayName: "Microsoft",
        icon: <WindowsOutlined />,
        color: "#0078d4",
        connectingText: "Connecting to Microsoft...",
        buttonText: "Sign in with Microsoft",
      };
    
    default:
      return {
        name: "unknown",
        displayName: "External Provider",
        icon: <GithubOutlined />, // fallback icon
        color: "#1890ff",
        connectingText: "Connecting...",
        buttonText: "Sign in",
      };
  }
};

export const getPopupWindowName = (authType: string): string => {
  return `${authType}-auth`;
};

export const isAuthEnabled = (authType: string): boolean => {
  return authType !== "none";
};