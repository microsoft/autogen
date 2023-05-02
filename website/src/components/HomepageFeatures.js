import React from 'react';
import clsx from 'clsx';
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'Find Quality Model at Your Fingertips',
    Svg: require('../../static/img/auto.svg').default,
    description: (
      <>
        FLAML finds accurate models or configurations with low computational resources
        for common ML/AI tasks.
        It frees users from selecting models and hyperparameters for training or inference.
        {/* It is fast and economical. */}
      </>
    ),
  },
  {
    title: 'Easy to Customize or Extend',
    Svg: require('../../static/img/extend.svg').default,
    description: (
      <>
        FLAML is designed easy to extend, such as adding custom learners or metrics.
        The customization level ranges smoothly from minimal
(training data and task type as only input) to full (tuning a user-defined function).
      </>
    ),
  },
  {
    title: 'Tune It Fast, Tune It As You Like',
    Svg: require('../../static/img/fast.svg').default,
    description: (
      <>
        FLAML offers a fast auto tuning tool powered by a novel cost-effective tuning approach.
        It is capable of handling large search space with heterogeneous evaluation cost
        and complex constraints/guidance/early stopping.
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
