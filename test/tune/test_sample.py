from flaml.tune.sample import (
    BaseSampler, PolynomialExpansionSet, Domain,
    uniform, quniform, choice, randint, qrandint, randn,
    qrandn, loguniform, qloguniform, lograndint, qlograndint)


def test_sampler():
    print(randn().sample(size=2))
    print(PolynomialExpansionSet(), BaseSampler())
    print(qrandn(2, 10, 2).sample(size=2))
    c = choice([1, 2])
    print(c.domain_str, len(c), c.is_valid(3))
    i = randint(1, 10)
    print(i.domain_str, i.is_valid(10))
    d = Domain()
    print(d.domain_str, d.is_function())
    d.default_sampler_cls = BaseSampler
    print(d.get_sampler())
