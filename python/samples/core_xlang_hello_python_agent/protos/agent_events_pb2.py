# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: agent_events.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'agent_events.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12\x61gent_events.proto\x12\x06\x61gents\"2\n\x0bTextMessage\x12\x13\n\x0btextMessage\x18\x01 \x01(\t\x12\x0e\n\x06source\x18\x02 \x01(\t\"\x18\n\x05Input\x12\x0f\n\x07message\x18\x01 \x01(\t\"\x1f\n\x0eInputProcessed\x12\r\n\x05route\x18\x01 \x01(\t\"\x19\n\x06Output\x12\x0f\n\x07message\x18\x01 \x01(\t\"\x1e\n\rOutputWritten\x12\r\n\x05route\x18\x01 \x01(\t\"\x1a\n\x07IOError\x12\x0f\n\x07message\x18\x01 \x01(\t\"%\n\x12NewMessageReceived\x12\x0f\n\x07message\x18\x01 \x01(\t\"%\n\x11ResponseGenerated\x12\x10\n\x08response\x18\x01 \x01(\t\"\x1a\n\x07GoodBye\x12\x0f\n\x07message\x18\x01 \x01(\t\" \n\rMessageStored\x12\x0f\n\x07message\x18\x01 \x01(\t\";\n\x12\x43onversationClosed\x12\x0f\n\x07user_id\x18\x01 \x01(\t\x12\x14\n\x0cuser_message\x18\x02 \x01(\t\"\x1b\n\x08Shutdown\x12\x0f\n\x07message\x18\x01 \x01(\tB\x1b\xaa\x02\x18Microsoft.AutoGen.Agentsb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'agent_events_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'\252\002\030Microsoft.AutoGen.Agents'
  _globals['_TEXTMESSAGE']._serialized_start=30
  _globals['_TEXTMESSAGE']._serialized_end=80
  _globals['_INPUT']._serialized_start=82
  _globals['_INPUT']._serialized_end=106
  _globals['_INPUTPROCESSED']._serialized_start=108
  _globals['_INPUTPROCESSED']._serialized_end=139
  _globals['_OUTPUT']._serialized_start=141
  _globals['_OUTPUT']._serialized_end=166
  _globals['_OUTPUTWRITTEN']._serialized_start=168
  _globals['_OUTPUTWRITTEN']._serialized_end=198
  _globals['_IOERROR']._serialized_start=200
  _globals['_IOERROR']._serialized_end=226
  _globals['_NEWMESSAGERECEIVED']._serialized_start=228
  _globals['_NEWMESSAGERECEIVED']._serialized_end=265
  _globals['_RESPONSEGENERATED']._serialized_start=267
  _globals['_RESPONSEGENERATED']._serialized_end=304
  _globals['_GOODBYE']._serialized_start=306
  _globals['_GOODBYE']._serialized_end=332
  _globals['_MESSAGESTORED']._serialized_start=334
  _globals['_MESSAGESTORED']._serialized_end=366
  _globals['_CONVERSATIONCLOSED']._serialized_start=368
  _globals['_CONVERSATIONCLOSED']._serialized_end=427
  _globals['_SHUTDOWN']._serialized_start=429
  _globals['_SHUTDOWN']._serialized_end=456
# @@protoc_insertion_point(module_scope)
