import React, { useState, useRef } from "react";
import { Input, Button, Alert, Spin, Tag } from "antd";
import { SendOutlined } from "@ant-design/icons";
import {
  toolMakerAPI,
  ToolMakerEvent,
  ToolComponentModel,
  ToolMakerStreamMessage,
} from "./api";

const ToolMakerLab: React.FC = () => {
  const [description, setDescription] = useState("");
  const [events, setEvents] = useState<ToolMakerEvent[]>([]);
  const [component, setComponent] = useState<ToolComponentModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<typeof toolMakerAPI | null>(null);

  const exampleTools = [
    "A tool that fetches the content of a web page",
    "A calculator tool that performs mathematical operations",
    "A tool that generates QR codes from text",
    "A tool that converts text to speech",
    "A tool that extracts text from images (OCR)",
    "A tool that validates email addresses",
    "A tool that generates secure random passwords",
    "A tool that converts currencies using live exchange rates",
  ];

  const handleExampleClick = (example: string) => {
    setDescription(example);
  };

  const handleStart = () => {
    setEvents([]);
    setComponent(null);
    setError(null);
    setLoading(true);
    wsRef.current = toolMakerAPI;
    wsRef.current.connect(
      (msg: ToolMakerStreamMessage) => {
        if ("event" in msg) {
          setEvents((prev) => [...prev, msg.event]);
        } else if ("component" in msg) {
          setComponent(msg.component);
          setLoading(false);
          wsRef.current?.close();
        } else if ("error" in msg) {
          setError(msg.error);
          setLoading(false);
          wsRef.current?.close();
        }
      },
      (err) => {
        setError("WebSocket error: " + err);
        setLoading(false);
      },
      () => {
        setLoading(false);
      }
    );
    setTimeout(() => {
      wsRef.current?.sendDescription(description);
    }, 200); // Give ws time to connect
  };

  return (
    <div className="">
      <h1 className="text-2xl font-bold mb-6">Tool Maker (Experimental)</h1>
      <p className="mb-4 text-secondary">
        This lab allows you to create and test new tools using natural language
        descriptions.
      </p>

      <div className="mb-4">
        <p className="text-sm font-medium mb-2 text-secondary">
          Try these examples:
        </p>
        <div className="flex flex-wrap gap-2">
          {exampleTools.map((example, idx) => (
            <Tag
              key={idx}
              className="cursor-pointer hover:bg-primary/10 transition-colors"
              onClick={() => handleExampleClick(example)}
            >
              {example}
            </Tag>
          ))}
        </div>
      </div>
      <div className="flex gap-2 mb-4">
        <Input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe your tool (e.g. 'A tool that fetches the content of a web page')"
          onPressEnter={handleStart}
          disabled={loading}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleStart}
          loading={loading}
          disabled={!description.trim() || loading}
        >
          Create
        </Button>
      </div>
      {error && <Alert type="error" message={error} className="mb-4" />}
      {loading && <Spin className="mb-4" />}
      <div className="mb-4">
        {events.map((event, idx) => (
          <Alert
            key={idx}
            type="info"
            message={event.status}
            description={event.content}
            className="mb-2"
          />
        ))}
      </div>
      {component && (
        <div className="border rounded p-4 bg-secondary/10">
          <h2 className="font-semibold mb-2">Generated Tool</h2>
          <pre className="bg-secondary/20 p-2 rounded text-xs overflow-x-auto mb-2">
            {JSON.stringify(component, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ToolMakerLab;
