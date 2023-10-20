import * as React from "react";
import { BeakerIcon, InformationCircleIcon } from '@heroicons/react/outline';
import SearchView from "../components/search";
import Layout from "../components/layout";
import LoginView from "../components/login";

// markup
const LoginPage = () => {
  const pageTitle = "Interaction Data Viewer";
  return (
    <Layout title="Sign In" showHeader={false}>
      <LoginView />
    </Layout>
  );
};

export default LoginPage;
