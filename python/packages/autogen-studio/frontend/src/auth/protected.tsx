import React, { useEffect } from "react";
import { navigate } from "gatsby";
import { useAuth } from "./context";
import { Spin } from "antd";

interface ProtectedRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  redirectTo = "/login",
}) => {
  const { isAuthenticated, isLoading, authType } = useAuth();

  useEffect(() => {
    // If not loading and auth is required (not 'none') and user is not authenticated, redirect
    if (!isLoading && authType !== "none" && !isAuthenticated) {
      navigate(redirectTo);
    }
  }, [isAuthenticated, isLoading, authType, redirectTo]);

  // Show loading indicator while checking auth status
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Spin size="large" tip="Loading..." />
      </div>
    );
  }

  // If auth type is 'none' or user is authenticated, render children
  if (authType === "none" || isAuthenticated) {
    return <>{children}</>;
  }

  // This should not be visible as we redirect, but as a fallback
  return null;
};

export default ProtectedRoute;
