import React from 'react';
import clsx from 'clsx';
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'Customizable and Convertible Agents ',
    Svg: require('../../static/img/auto.svg').default,
    description: (
      <>
        AutoGen provides customizable and convertible agents that can be backed by 
        LLMs, humans, tools, or a combination of them.
      </>
    ),
  },
  {
    title: 'Flexible Conversation Patterns',
    Svg: require('../../static/img/extend.svg').default,
    description: (
      <>
      AutoGen supports flexible conversation patterns for realizing complex and dynamic workflows. 
      </>
    ),
  },
//   {
//     title: 'Easy to Customize or Extend',
//     Svg: require('../../static/img/extend.svg').default,
//     description: (
//       <>
//         FLAML is designed easy to extend, such as adding custom learners or metrics.
//         The customization level ranges smoothly from minimal
// (training data and task type as only input) to full (tuning a user-defined function).
//       </>
//     ),
//   },
  {
    title: 'Diverse Applications',
    Svg: require('../../static/img/fast.svg').default,
    description: (
      <>
        AutoGen offers a collection of working systems spanning span a wide range of applications from various domains and complexities.
      </>
    ),
  },
];

function Feature({Svg, title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} alt={title} />
      </div>
      <div className="text--center padding-horiz--md">
        <h3>{title}</h3>
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
