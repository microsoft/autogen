AGNext
------

AGNext is a framework for building multi-agent applications. It is designed to be easy to use, flexible, and scalable.

At a high level it provides both a framework for inter-agent communication and a set of components for building and managing agents.

:doc:`Agents <core-concepts/agent>` are hosted by and managed by a :doc:`runtime <core-concepts/runtime>`.
AGNext supports both RPC or event based based
communication between agents, allowing for a :doc:`diverse set of agent patterns
<core-concepts/patterns>`. AGNext provides default agent implementations for
common uses, such as chat completion agents, but also allows for fully custom agents.

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

.. toctree::
    :caption: Guides
    :hidden:

    guides/type-routed-agent
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

