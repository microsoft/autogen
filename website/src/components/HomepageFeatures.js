import React from 'react';
import clsx from 'clsx';
import { Link } from 'react-router-dom'; 
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'Customizable and Convertible Agents ',
    Svg: require('../../static/img/auto.svg').default,
    docLink: './docs/getting-started',
    description: (
      <>
        AutoGen provides customizable and convertible agents that can be backed by 
        LLMs, humans, tools, or a combination of them.
      </>
    ),
  },
  {
    title: 'Flexible Multi-Conversation Patterns',
    Svg: require('../../static/img/extend.svg').default,
    docLink: './docs/getting-started',
    description: (
      <>
      AutoGen supports flexible conversation patterns for realizing complex and dynamic workflows. 
      </>
    ),
  },
  {
    title: 'Diverse Applications',
    Svg: require('../../static/img/fast.svg').default,
    docLink: './docs/getting-started',
    description: (
      <>
        AutoGen offers a collection of working systems spanning span a wide range of applications from various domains and complexities.
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
