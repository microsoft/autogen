import os

RAG_MINIMUM_MESSAGE_LENGTH = os.environ.get("RAG_MINIMUM_MESSAGE_LENGTH", 5)
CHROMADB_MAX_BATCH_SIZE = os.environ.get("CHROMADB_MAX_BATCH_SIZE", 40000)
UPDATE_CONTEXT_TRIGGER_WORDS = ["update context", "however", "could you provide"]
TERMINATE_TRIGGER_WORDS = ["terminate", "goodbye", "bye", "exit", "quit", "stop", "end"]
