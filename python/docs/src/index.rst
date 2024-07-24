AGNext
------

AGNext is a framework for building multi-agent applications with AI agents.

At a high level, it provides a framework for inter-agent communication and a 
suite of independent components for building and managing agents.
You can implement agents in 
different programming languages and deploy them on different machines across organizational boundaries.
You can also implement agents using other agent frameworks and run them in AGNext.

To get you started quickly, we offers
`a suite of samples <https://github.com/microsoft/agnext/tree/main/python/samples>`_.

To learn about the core concepts of AGNext, read the following sections:

- `Overview <core-concepts/overview>`_ on the architecture design.
- `Foundation <core-concepts/foundation>`_ on agent runtime and inter-agent communication.
- `AI Agents <core-concepts/ai-agents>`_ on how to build AI agents.
- `Multi-Agent Patterns <core-concepts/patterns>`_ on multi-agent collaboration patterns.

.. toctree::
    :caption: Getting started
    :hidden:

    getting-started/installation

.. toctree::
    :caption: Core Concepts
    :hidden:

    core-concepts/overview
    core-concepts/foundation
    core-concepts/ai-agents
    core-concepts/patterns

.. toctree::
    :caption: Guides
    :hidden:

    guides/logging
    guides/worker-protocol

.. toctree::
    :caption: Cookbook
    :hidden:

    cookbook/type-routed-agent
    cookbook/azure-openai-with-aad-auth
    cookbook/termination-with-intervention
    cookbook/buffered-memory
    cookbook/extracting-results-with-an-agent


.. toctree::
    :caption: Reference
    :hidden:

    reference/agnext.components
    reference/agnext.application
    reference/agnext.core
    reference/agnext.worker

.. toctree::
    :caption: Other
    :hidden:

    contributing

