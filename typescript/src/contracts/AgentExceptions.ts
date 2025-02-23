export class AgentException extends Error {
  constructor(message?: string) {
    super(message);
    this.name = "AgentException";
  }
}

export class CantHandleException extends AgentException {
  constructor(message?: string) {
    super(message || "The handler cannot process the given message.");
    this.name = "CantHandleException";
  }
}

export class UndeliverableException extends AgentException {
  constructor(message?: string) {
    super(message || "The message cannot be delivered.");
    this.name = "UndeliverableException";
  }
}

export class MessageDroppedException extends AgentException {
  constructor(message?: string) {
    super(message || "The message was dropped.");
    this.name = "MessageDroppedException";
  }
}

export class NotAccessibleError extends AgentException {
  constructor(message?: string) {
    super(message || "The requested value is not accessible.");
    this.name = "NotAccessibleError";
  }
}