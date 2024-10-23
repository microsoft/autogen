import React from "react";
import clsx from "clsx";
import styles from "./styles.module.css";

function PopularResources() {
  return (
    <>
      <section className={clsx("home-container", styles.features)}>
        <div className={clsx("row margin-horiz--lg")}>
          <div className={clsx("col col--2")}>
            <h3 className="padding-top--lg container-h3">
              Popular resources
            </h3>
          </div>
          <div className={clsx("col col--10")}>
            <div className={clsx("row")}>
              <div className={clsx("col col--4 padding--lg", styles.posRelative)}>
                <div className={styles.iframeDiv}>
                  <iframe
                    src="https://www.youtube.com/embed/RLwyXRVvlNk"
                    className={clsx(styles.responsiveIframe)}
                    title="Learn AutoGen on DeepLearningAI"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  ></iframe>
                  <a
                    href="https://www.youtube.com/watch?v=RLwyXRVvlNk"
                  >
                    Foundation Capital Interview with Dr. Chi Wang
                  </a>
                </div>
              </div>
              <div className={clsx("col col--4 padding--lg", styles.posRelative)}>
                <div className={styles.iframeDiv}>
                  <iframe
                    src="https://www.youtube.com/embed/TBNTH-fwGPE"
                    className={clsx(styles.responsiveIframe)}
                    title="Learn AutoGen on DeepLearningAI"
                    frameBorder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  ></iframe>
                  <a
                    href="https://www.youtube.com/watch?v=TBNTH-fwGPE"
                  >
                    Learn AutoGen on DeepLearningAI
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export default PopularResources;
