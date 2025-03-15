import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/context";
import { Spin, Typography, Alert } from "antd";
import Layout from "../components/layout";
import { graphql } from "gatsby";

const { Title } = Typography;

const CallbackPage = ({ data, location }: any) => {
  const { handleAuthCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const processAuth = async () => {
      try {
        // Get the authorization code and state from URL search params
        const params = new URLSearchParams(location.search);
        const code = params.get("code");
        const state = params.get("state");
        const authError = params.get("error");

        if (authError) {
          setError(`Authentication error: ${authError}`);
          setIsProcessing(false);
          return;
        }

        if (!code) {
          setError("No authorization code found in the URL");
          setIsProcessing(false);
          return;
        }

        // Handle the authorization code - for popup window
        // The actual token handling is done by the backend HTML response
        await handleAuthCallback(code, state || undefined);
        setIsProcessing(false);
      } catch (err) {
        console.error("Error during auth callback:", err);
        setError("Failed to complete authentication");
        setIsProcessing(false);
      }
    };

    processAuth();
  }, [location.search, handleAuthCallback]);

  return (
    <Layout
      meta={data.site.siteMetadata}
      title="Authenticating"
      link="/callback"
      showHeader={false}
    >
      <div className="flex flex-col items-center justify-center h-screen">
        {isProcessing ? (
          <>
            <Spin size="large" />
            <Title level={4} className="mt-4">
              Completing Authentication...
            </Title>
          </>
        ) : error ? (
          <Alert
            message="Authentication Error"
            description={error}
            type="error"
            showIcon
            className="max-w-md"
          />
        ) : (
          <Alert
            message="Authentication Successful"
            description="You have been successfully authenticated. You can close this window now."
            type="success"
            showIcon
            className="max-w-md"
          />
        )}
      </div>
    </Layout>
  );
};

export const query = graphql`
  query CallbackPageQuery {
    site {
      siteMetadata {
        description
        title
      }
    }
  }
`;

export default CallbackPage;
