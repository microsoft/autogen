import React, { createContext, useState, useEffect, useContext } from "react";
import { authAPI, User } from "./api";
import { message } from "antd";
import { navigate } from "gatsby";
import {
  sanitizeUrl,
  sanitizeRedirectUrl,
  isValidMessageOrigin,
  isValidUserObject,
} from "../components/utils/security-utils";
import { getAuthProviderInfo } from "./utils";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authType: string;
  login: () => Promise<string>;
  logout: () => void;
  handleAuthCallback: (code: string, state?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = "auth_token";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [authType, setAuthType] = useState<string>("none");

  // Function to get token from localStorage
  const getToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  };

  // Function to save token to localStorage
  const saveToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
  };

  // Function to remove token from localStorage
  const removeToken = (): void => {
    localStorage.removeItem(TOKEN_KEY);
  };

  // Load user on initial render if token exists
  useEffect(() => {
    const loadUser = async () => {
      try {
        // Check auth type first
        const { type } = await authAPI.checkAuthType();
        setAuthType(type);

        // If auth is disabled, set default user and complete loading
        if (type === "none") {
          setUser({
            id: "guestuser@gmail.com",
            name: "Guest User",
          });
          setIsLoading(false);
          return;
        }

        const token = getToken();
        if (!token) {
          setIsLoading(false);
          return;
        }

        // Load user data with token
        const userData = await authAPI.getCurrentUser(token);
        setUser(userData);
      } catch (error) {
        console.error("Failed to load user:", error);
        removeToken(); // Clear invalid token
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  // Setup message listener for popup window communication
  useEffect(() => {
    const handleAuthMessage = (event: MessageEvent) => {
      if (!isValidMessageOrigin(event.origin)) {
        console.error(
          `Rejected message from untrusted origin: ${event.origin}`
        );
        return;
      }

      const data = event.data;

      if (data.type === "auth-success" && data.token && data.user) {
        if (!isValidUserObject(data.user)) {
          console.error("Invalid user data structure received");
          return;
        }

        if (data.user.avatar_url) {
          data.user.avatar_url = sanitizeUrl(data.user.avatar_url);
        }

        // Store token
        saveToken(data.token);

        // Update user state
        setUser(data.user);

        // Show success message with provider name
        const providerInfo = getAuthProviderInfo(data.user.provider || authType);
        message.success(`Successfully signed in with ${providerInfo.displayName}`);

        // Redirect to home
        navigate(sanitizeRedirectUrl("/"));
      } else if (data.type === "auth-error") {
        const providerInfo = getAuthProviderInfo(authType);
        message.error(`${providerInfo.displayName} authentication failed: ${data.error}`);
      }
    };

    window.addEventListener("message", handleAuthMessage);

    return () => {
      window.removeEventListener("message", handleAuthMessage);
    };
  }, []);

  // Login function - gets login URL but doesn't redirect
  // (redirection is handled in the login component with popup)
  const login = async (): Promise<string> => {
    try {
      if (authType === "none") {
        // No auth required
        return "";
      }

      const loginUrl = await authAPI.getLoginUrl();
      return loginUrl || "";
    } catch (error) {
      message.error("Failed to initiate login");
      console.error("Login error:", error);
      return "";
    }
  };

  // Handle auth callback from provider
  const handleAuthCallback = async (
    code: string,
    state?: string
  ): Promise<void> => {
    try {
      // For popup window approach
      if (window.opener) {
        // This is handled by the backend HTML response
        // Just display a message in the popup
        message.success(
          "Authentication successful! You can close this window."
        );
        return;
      }

      // For direct redirect approach (backup)
      const { token, user } = await authAPI.handleCallback(code, state);
      saveToken(token);
      setUser(user);
      message.success("Successfully logged in");
      navigate("/"); // Redirect to home after successful login
    } catch (error) {
      message.error("Authentication failed");
      console.error("Auth callback error:", error);
    }
  };

  // Logout function
  const logout = (): void => {
    removeToken();
    setUser(null);
    message.info("Successfully logged out");
    navigate("/login");
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    authType,
    login,
    logout,
    handleAuthCallback,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Hook to use auth context
export const useAuth = (): AuthContextType => {
  if (typeof window === "undefined") {
    // Return default values or empty implementation
    return {
      user: null,
      isAuthenticated: false,
      isLoading: true,
      authType: "none",
      login: async () => "",
      logout: () => {},
      handleAuthCallback: async () => {},
    } as AuthContextType;
  }
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
