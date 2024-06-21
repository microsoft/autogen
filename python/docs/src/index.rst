AGNext
------

AGNext is a framework for building multi-agent applications. It is designed to be easy to use, flexible, and scalable.

At a high level it provides both a framework for inter-agent communication and a set of components for building and managing agents.

:doc:`Agents <core-concepts/agent>` are hosted by and managed by a :doc:`runtime <core-concepts/runtime>`.
AGNext supports both RPC or event based based
communication between agents, allowing for a :doc:`diverse set of agent patterns
<core-concepts/patterns>`. AGNext provides default agent implementations for
common uses, such as chat completion agents, but also allows for fully custom agents.

AGNext's developer API consists of the following layers:

- :doc:`core <reference/agnext.core>` - The core interfaces that defines agent 
    and runtime.
- :doc:`application <reference/agnext.application>` - Implementations of the runtime 
    and other modules (e.g., logging) for building applications.
- :doc:`components <reference/agnext.components>` - Interfaces and implementations 
    for agents, models, memory, and tools.
- :doc:`chat <reference/agnext.chat>` - High-level API for creating demos and
    experimenting with multi-agent patterns. It offers pre-built agents, patterns, 
    message types, and memory stores.



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
    guides/group-chat-coder-reviewer
    guides/azure-openai-with-aad-auth


.. toctree::
    :caption: Reference
    :hidden:

    reference/agnext.components
    reference/agnext.application
    reference/agnext.chat
    reference/agnext.core

.. toctree::
    :caption: Other
    :hidden:

    contributing

