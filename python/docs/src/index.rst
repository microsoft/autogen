AGNext
------

AGNext is a framework for building multi-agent applications.

At a high level, it provides a framework for inter-agent communication and a 
suite of independent components for building and managing agents. It models agents as 
independent actors communicating via messages. You can implement agents in 
different languages and run them on different machines across organizational boundaries.
You can also implement agents using other agent frameworks and run them in AGNext.

:doc:`Agents <core-concepts/agent>` are hosted by and managed by a :doc:`runtime <core-concepts/runtime>`.
AGNext supports both RPC-like direct messaging and event based
communication between agents, allowing for a :doc:`diverse set of agent patterns
<core-concepts/patterns>`.

AGNext's developer API consists of the following layers:

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
    getting-started/tutorial

.. toctree::
    :caption: Core Concepts
    :hidden:

    core-concepts/runtime
    core-concepts/agent
    core-concepts/patterns
    core-concepts/memory
    core-concepts/tools
    core-concepts/cancellation
    core-concepts/logging
    core-concepts/namespace

.. toctree::
    :caption: Guides
    :hidden:

    guides/type-routed-agent
    guides/azure-openai-with-aad-auth
    guides/termination-with-intervention


.. toctree::
    :caption: Reference
    :hidden:

    reference/agnext.components
    reference/agnext.application
    reference/agnext.core

.. toctree::
    :caption: Other
    :hidden:

    contributing

