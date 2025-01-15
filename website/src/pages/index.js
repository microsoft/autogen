import React from "react";
import clsx from "clsx";
import Layout from "@theme/Layout";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import styles from "./index.module.css";
import HomepageFeatures from "../components/HomepageFeatures";

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header className={clsx("hero hero--primary", styles.heroBanner)}>
      <div className="container">
        <h1 className="hero__title">{siteConfig.title}</h1>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>

          <div className={styles.buttonWrapper}>
            <Link
              className={clsx(
                "button button--secondary button--lg",
                styles.buttonLink
              )}
              to="https://microsoft.github.io/autogen/stable/"
            >
              Get started with 0.4
            </Link>
            <p className={styles.buttonTagline}>
            The new event driven, asynchronous architecture for AutoGen
            </p>
          </div>
          <div className={styles.buttonWrapper}>
            <Link
              className="button button--secondary button--lg"
              to="/docs/Getting-Started"
            >
              Continue with 0.2
            </Link>
            <p className={styles.buttonTagline}></p>
          </div>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={`AutoGen`}
      description="Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework"
    >
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
