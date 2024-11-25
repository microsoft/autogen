# Agent Worker Protocol

## System architecture

The system consists of multiple processes, each being either a _service_ process or a _worker_ process.
Worker processes host application code (agents) and connect to a service process.
Workers advertise the agents which they support to the service, so the service can decide which worker to place agents on.
Service processes coordinate placement of agents on worker processes and facilitate communication between agents.

Agent instances are identified by the tuple of `(namespace: str, name: str)`.
Both _namespace_ and _name_ are application-defined.
The _namespace_ has no semantics implied by the system: it is free-form, and any semantics are implemented by application code.
The _name_ is used to route requests to a worker which supports agents with that name.
Workers advertise the set of agent names which they are capable of hosting to the service.
Workers activate agents in response to messages received from the service.
The service uses the _name_ to determine where to place currently-inactive agents, maintaining a mapping from agent name to a set of workers which support that agent.
The service maintains a _directory_ mapping active agent ids to worker processes which host the identified agent.

### Agent lifecycle

Agents are never explicitly created or destroyed. When a request is received for an agent which is not currently active, it is the responsibility of the service to select a worker which is capable of hosting that agent, and to route the request to that worker.

## Worker protocol flow

The worker protocol has three phases, following the lifetime of the worker: initialization, operation, and termination.

### Initialization

When the worker process starts, it initiates a connection to a service process, establishing a bi-directional communication channel which messages are passed across.
Next, the worker issues zero or more `RegisterAgentType(name: str)` messages, which tell the service the names of the agents which it is able to host.

* TODO: What other metadata should the worker give to the service?
* TODO: Should we give the worker a unique id which can be used to identify it for its lifetime? Should we allow this to be specified by the worker process itself?

### Operation

Once the connection is established, and the service knows which agents the worker is capable of hosting, the worker may begin receiving requests for agents which it must host.
Placement of agents happens in response to an `Event(...)` or `RpcRequest(...)` message.
The worker maintains a _catalog_ of locally active agents: a mapping from agent id to agent instance.
If a message arrives for an agent which does not have a corresponding entry in the catalog, the worker activates a new instance of that agent and inserts it into the catalog.
The worker dispatches the message to the agent:

* For an `Event`, the agent processes the message and no response is generated.
* For an `RpcRequest` message, the agent processes the message and generates a response of type `RpcResponse`. The worker routes the response to the original sender.

The worker maintains a mapping of outstanding requests, identified by `RpcRequest.id`, to a promise for a future `RpcResponse`.
When an `RpcResponse` is received, the worker finds the corresponding request id and fulfils the promise using that response.
If no response is received in a specified time frame (eg, 30s), the worker breaks the promise with a timeout error.

### Termination

When the worker is ready to shutdown, it closes the connection to the service and terminates. The service de-registers the worker and all agent instances which were hosted on it.
