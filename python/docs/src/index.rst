AGNext
------

AGNext is a framework for building multi-agent applications.

At a high level, it provides a framework for inter-agent communication and a 
suite of independent components for building and managing agents.
You can implement agents in 
different programming languages and run them on different machines across organizational boundaries.
You can also implement agents using other agent frameworks and run them in AGNext.

Please read :doc:`Core Concepts <getting-started/core-concepts>` for 
a detailed overview of AGNext's architecture and design.

AGNext's API consists of the following modules:

- :doc:`core <reference/agnext.core>` - The core interfaces that defines agent and runtime.
- :doc:`application <reference/agnext.application>` - Implementations of the runtime and other modules (e.g., logging) for building applications.
- :doc:`components <reference/agnext.components>` - Independent agent-building components: agents, models, memory, and tools.

To get you started quickly, we also offers
`a suite of examples <https://github.com/microsoft/agnext/tree/main/python/examples>`_
that demonstrate how to use AGNext.

.. toctree::
    :caption: Getting started
    :hidden:

    getting-started/installation
    getting-started/core-concepts

.. toctree::
    :caption: Guides
    :hidden:

    guides/components
    guides/patterns
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

