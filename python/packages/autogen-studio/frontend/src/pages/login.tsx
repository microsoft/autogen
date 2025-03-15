import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/context";
import { navigate } from "gatsby";
import { Button, Card, Typography, Space, Spin, message } from "antd";
import { GithubOutlined } from "@ant-design/icons";
import Layout from "../components/layout";
import { graphql } from "gatsby";
import Icon from "../components/icons";

const { Title, Text } = Typography;

// Use the same token key as in context.tsx
const TOKEN_KEY = "auth_token";

const LoginPage = ({ data }: any) => {
  const { isAuthenticated, isLoading, login, authType } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  useEffect(() => {
    // If user is already authenticated, redirect to home
    if (isAuthenticated && !isLoading) {
      navigate("/");
    }
  }, [isAuthenticated, isLoading]);

  // If auth type is 'none', redirect to home
  useEffect(() => {
    if (authType === "none" && !isLoading) {
      navigate("/");
    }
  }, [authType, isLoading]);

  const handleLogin = async () => {
    try {
      setIsLoggingIn(true);
      const loginUrl = await login();

      if (!loginUrl) {
        message.error("Failed to get login URL");
        setIsLoggingIn(false);
        return;
      }

      // Open a popup window for auth
      const width = 600;
      const height = 700;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;

      const popup = window.open(
        loginUrl,
        "github-auth",
        `width=${width},height=${height},top=${top},left=${left}`
      );

      // Check if popup was blocked
      if (!popup || popup.closed || typeof popup.closed === "undefined") {
        message.error(
          "Popup was blocked by browser. Please allow popups for this site."
        );
        setIsLoggingIn(false);
        return;
      }

      // Set a timer to check if the popup is closed without completing authentication
      const checkPopupInterval = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkPopupInterval);
          setIsLoggingIn(false);
        }
      }, 1000);
    } catch (error) {
      console.error("Login error:", error);
      message.error("Failed to initiate login");
      setIsLoggingIn(false);
    }
  };

  if (isLoading) {
    return (
      <Layout meta={data.site.siteMetadata} title="Login" link="/login">
        <div className="flex items-center justify-center h-screen">
          <Spin size="large" tip="Loading..." />
        </div>
      </Layout>
    );
  }

  return (
    <Layout
      meta={data.site.siteMetadata}
      title="Login"
      link="/login"
      showHeader={true}
      restricted={false}
    >
      <div className="flex items-center justify-center h-[calc(100vh-164px)]">
        <div className="w-full rounded bg-secondary max-w-md p-8 sxhadow-sm">
          <div className="text-center mb-8">
            <div className="mb-3">
              <Icon icon="app" size={12} />
            </div>
            <div className="text-2xl mb-1 font-semibold text-primary">
              Sign in to {data.site.siteMetadata.title}
            </div>
            <div className="text-secondary text-sm">
              {" "}
              Build and prototype multi-agent applications
            </div>
          </div>

          <Space direction="vertical" className="w-full">
            <Button
              type="primary"
              size="large"
              icon={<GithubOutlined />}
              onClick={handleLogin}
              loading={isLoggingIn}
              block
            >
              {isLoggingIn ? "Connecting to GitHub..." : "Sign in with GitHub"}
            </Button>
          </Space>
        </div>
      </div>
    </Layout>
  );
};

export const query = graphql`
  query LoginPageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default LoginPage;
