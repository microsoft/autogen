import React from 'react';
import clsx from 'clsx';
import styles from './HomepageFeatures.module.css';

const FeatureList = [
  {
    title: 'TODO',
    Svg: require('../../static/img/auto.svg').default,
    description: (
      <>
        TODO
      </>
    ),
  },
  {
    title: 'TODO',
    Svg: require('../../static/img/extend.svg').default,
    description: (
      <>
        TODO  
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
    title: 'TODO',
    Svg: require('../../static/img/fast.svg').default,
    description: (
      <>
        TODO
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
