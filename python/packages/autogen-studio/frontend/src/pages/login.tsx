import React, { useEffect } from "react";
import { useAuth } from "../auth/context";
import { navigate } from "gatsby";
import { Button, Card, Typography, Space, Spin } from "antd";
import { GithubOutlined } from "@ant-design/icons";
import Layout from "../components/layout";
import { graphql } from "gatsby";

const { Title, Text } = Typography;

const LoginPage = ({ data }: any) => {
  const { isAuthenticated, isLoading, login, authType } = useAuth();

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
    await login();
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
      showHeader={false}
    >
      <div className="flex items-center justify-center h-screen">
        <Card className="w-full max-w-md p-8 shadow-lg">
          <div className="text-center mb-8">
            <Title level={3}>Sign in to {data.site.siteMetadata.title}</Title>
            <Text type="secondary">Access your teams and projects</Text>
          </div>

          <Space direction="vertical" className="w-full">
            <Button
              type="primary"
              size="large"
              icon={<GithubOutlined />}
              onClick={handleLogin}
              block
            >
              Sign in with GitHub
            </Button>
          </Space>
        </Card>
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
