import React from 'react';
import clsx from 'clsx';
import { Link } from 'react-router-dom';
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'Multi-Agent Conversation Framework',
    Svg: require('../../static/img/conv_2.svg').default,
    docLink: './docs/Use-Cases/agent_chat',
    description: (
      <>
        AutoGen provides multi-agent conversation framework as a high-level abstraction. With this framework, one can conveniently build LLM workflows.
      </>
    ),
  },
  {
    title: 'Easily Build Diverse Applications',
    Svg: require('../../static/img/autogen_app.svg').default,
    docLink: './docs/Use-Cases/agent_chat#diverse-applications-implemented-with-autogen',
    description: (
      <>
        AutoGen offers a collection of working systems spanning a wide range of applications from various domains and complexities.
      </>
    ),
  },
  {
    title: 'Enhanced LLM Inference & Optimization',
    Svg: require('../../static/img/extend.svg').default,
    docLink: './docs/Use-Cases/enhanced_inference',
    description: (
      <>
      AutoGen supports enhanced LLM inference APIs, which can be used to improve inference performance and reduce cost.
      </>
    ),
  },
];

function Feature({Svg, title, description, docLink}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} alt={title} />
      </div>
      <div className="text--center padding-horiz--md">
        <Link to={docLink}>
            <h3>{title}</h3>
        </Link>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
