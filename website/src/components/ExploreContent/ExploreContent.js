import React, { useState } from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import styles from "./styles.module.css";

const firstDataRow = [
  {
    title: "Get Started",
    link: "/docs/Getting-Started",
    description: (
      <>
        Learn how to get start with AutoGen. Follow the instruction to quickly build-up your first AutoGen application.
      </>
    ),
  },
  {
    title: "Tutorial",
    link: "docs/tutorial/introduction",
    description: (
      <>
        This tutorial introduces basic concepts and building blocks of AutoGen.
      </>
    ),
  },
  {
    title: "User Guide",
    link: "docs/topics",
    description: (
      <>
        Users' guide to different functionalities of AutoGen, including CodeExecution, GroupChat, and more.
      </>
    ),
  },
];

const secondDataRow = [
  {
    title: "Examples",
    link: "docs/Examples",
    description: (
      <>
        Learn different examples demonstrating the usage of AutoGen in various scenarios.
      </>
    ),
  },
  {
    title: "Applications",
    link: "docs/Gallery",
    description: (
      <>
        A collection of different applications built using AutoGen.
      </>
    ),
  },
  {
    title: "Contributions",
    link: "docs/contributor-guide/contributing",
    description: (
      <>
        Learn about how you can contribute to AutoGen and this documentation, including pushing patches, code review and more.
      </>
    ),
  },
];

function Feature({ title, link, description }) {
  const [hovered, setHovered] = useState(false);
  const toggleHover = () => setHovered(!hovered);

  return (
    <div className={clsx("col col--4", styles.feature)}>
      <Link
        to={useBaseUrl(link)}
        className={
          hovered
            ? clsx("padding--lg margin-bottom--lg item shadow--tl", styles.card)
            : clsx("padding--lg margin-bottom--lg item shadow--lw", styles.card)
        }
        onMouseOver={toggleHover}
        onMouseOut={toggleHover}
      >
        <div>
          <div className={clsx(styles.titles)}>
            <h4>{title}</h4>
            <p>{description}</p>
          </div>
        </div>
      </Link>
    </div>
  );
}

function Features() {
  return (
    <>
      {firstDataRow && firstDataRow.length > 0 && (
        <section className={clsx("home-container", styles.features)}>
          <div className={clsx("row margin-horiz--lg")}>
            <div className={clsx("col col--2")}>
              <h3 className="container-h3">Explore content</h3>
            </div>
            <div className={clsx("col col--10")}>
              <div className={clsx("row")}>
                {firstDataRow.map((props, idx) => (
                  <Feature key={idx} {...props} />
                ))}
              </div>
            </div>
            <div className={clsx("col col--2")}></div>
            <div className={clsx("col col--10")}>
              <div className={clsx("row")}>
                {secondDataRow.map((props, idx) => (
                  <Feature key={idx} {...props} />
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </>
  );
}

export default Features;
