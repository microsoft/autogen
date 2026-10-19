/**
 * Base class for all agent-related exceptions.
 */
export class AgentException extends Error {
  /**
   * Creates a new instance of the AgentException class.
   * @param message Optional error message
   */
  constructor(message?: string) {
    super(message);
    this.name = "AgentException";
  }
}

/**
 * Exception thrown when a handler cannot process the given message.
 */
export class CantHandleException extends AgentException {
  /**
   * Creates a new instance of the CantHandleException class.
   * @param message Optional custom error message
   */
  constructor(message?: string) {
    super(message || "The handler cannot process the given message.");
    this.name = "CantHandleException";
  }
}

/**
 * Exception thrown when a message cannot be delivered.
 */
export class UndeliverableException extends AgentException {
  /**
   * Creates a new instance of the UndeliverableException class.
   * @param message Optional custom error message
   */
  constructor(message?: string) {
    super(message || "The message cannot be delivered.");
    this.name = "UndeliverableException";
  }
}

/**
 * Exception thrown when a message is dropped.
 */
export class MessageDroppedException extends AgentException {
  /**
   * Creates a new instance of the MessageDroppedException class.
   * @param message Optional custom error message
   */
  constructor(message?: string) {
    super(message || "The message was dropped.");
    this.name = "MessageDroppedException";
  }
}

/**
 * Exception thrown when an attempt is made to access an unavailable value, 
 * such as a remote resource.
 */
export class NotAccessibleError extends AgentException {
  /**
   * Creates a new instance of the NotAccessibleError class.
   * @param message Optional custom error message
   */
  constructor(message?: string) {
    super(message || "The requested value is not accessible.");
    this.name = "NotAccessibleError";
  }
}