import React, { useCallback, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from "react-flow";
import { User, Bot, Code, Brain } from "lucide-react";
import { Tooltip } from "antd";
import "reactflow/dist/style.css";

import {
  Message,
  AgentConfig,
  AgentTypes,
  MessageConfig,
} from "../../../types/datamodel";

interface AgentFlowProps {
  messages: Message[];
  agents?: AgentConfig[];
  onMessageHighlight?: (messageId: string) => void;
  onMessageSelect?: (messageId: string) => void;
  highlightedMessageId?: string;
  selectedMessageId?: string;
}

const AgentFlowDiagram = ({
  messages,
  agents = [],
  onMessageHighlight,
  onMessageSelect,
  highlightedMessageId,
  selectedMessageId,
}: AgentFlowProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Get appropriate icon for agent type
  const getAgentIcon = (agentType: AgentTypes) => {
    switch (agentType) {
      case "CodingAssistantAgent":
        return Code;
      case "AssistantAgent":
        return Brain;
      default:
        return Bot;
    }
  };

  // Custom node to represent agents with icons
  const AgentNode = ({ data }) => {
    const Icon = data.type === "user" ? User : getAgentIcon(data.agentType);
    const isActive = data.isActive;

    const tooltipContent = (
      <div>
        <div className="font-semibold">{data.name}</div>
        {data.description && (
          <div className="text-xs mt-1">{data.description}</div>
        )}
        {data.messageCount > 0 && (
          <div className="text-xs mt-1">Messages: {data.messageCount}</div>
        )}
      </div>
    );

    return (
      <Tooltip
        title={tooltipContent}
        placement="top"
        overlayClassName="agent-tooltip"
      >
        <div
          className={`
          flex flex-col items-center p-2 bg-white rounded-lg border-2 
          ${isActive ? "border-blue-400 shadow-lg" : "border-gray-200"}
          ${data.isHighlighted ? "ring-2 ring-blue-300" : ""}
          transition-all duration-200
        `}
        >
          <div
            className={`
            p-2 rounded-full 
            ${isActive ? "bg-blue-100 animate-pulse" : "bg-gray-100"}
            ${data.isHighlighted ? "bg-blue-50" : ""}
          `}
          >
            <Icon
              className={`
                ${isActive ? "text-blue-500" : "text-gray-500"}
                ${data.isHighlighted ? "text-blue-400" : ""}
              `}
              size={24}
            />
          </div>
          <div className="mt-1 text-sm font-medium text-gray-700">
            {data.name}
          </div>
        </div>
      </Tooltip>
    );
  };

  const nodeTypes = {
    agent: AgentNode,
  };

  // Calculate node positions in a circular layout
  const getNodePosition = (index: number, total: number) => {
    const radius = 150;
    const angle = (index * 2 * Math.PI) / total;
    return {
      x: radius * Math.cos(angle) + radius,
      y: radius * Math.sin(angle) + radius,
    };
  };

  // Update flow diagram when messages or agents change
  useEffect(() => {
    if (!messages?.length) return;

    // Create nodes for all agents plus user
    const allParticipants = [
      { name: "User", agent_type: "user" as AgentTypes },
      ...agents,
    ];

    // Count messages per agent
    const messageCountsByAgent = messages.reduce((acc, msg) => {
      acc[msg.config.source] = (acc[msg.config.source] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Create nodes
    const flowNodes = allParticipants.map((agent, idx) => {
      const position = getNodePosition(idx, allParticipants.length);
      const lastMessage = messages[messages.length - 1];

      return {
        id: agent.name,
        type: "agent",
        position,
        data: {
          name: agent.name,
          agentType: agent.agent_type,
          description: agent.description,
          isActive: lastMessage?.config.source === agent.name,
          isHighlighted: false,
          messageCount: messageCountsByAgent[agent.name] || 0,
          type: agent.agent_type === "user" ? "user" : "bot",
        },
      };
    });

    // Create edges based on message flow
    const flowEdges = messages.map((msg, idx) => {
      const messageId = `${msg.run_id}-${idx}`;
      const source = msg.config.source;
      const target =
        messages[idx + 1]?.config.source || allParticipants[0].name;

      return {
        id: messageId,
        source,
        target,
        animated: idx === messages.length - 1,
        style: {
          stroke: getEdgeStyle(messageId),
          strokeWidth: getEdgeWidth(messageId),
        },
        type: "smoothstep",
        data: {
          messageIndex: idx,
          content: msg.config.content,
          usage: msg.config.models_usage,
        },
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [messages, agents, highlightedMessageId, selectedMessageId]);

  // Edge styling helpers
  const getEdgeStyle = useCallback(
    (messageId: string) => {
      if (messageId === selectedMessageId) return "#1890ff";
      if (messageId === highlightedMessageId) return "#40a9ff";
      return "#bfbfbf";
    },
    [highlightedMessageId, selectedMessageId]
  );

  const getEdgeWidth = useCallback(
    (messageId: string) => {
      if (messageId === selectedMessageId) return 3;
      if (messageId === highlightedMessageId) return 2;
      return 1;
    },
    [highlightedMessageId, selectedMessageId]
  );

  // Edge interaction handlers
  const onEdgeMouseEnter = useCallback(
    (_, edge) => {
      onMessageHighlight?.(edge.id);
    },
    [onMessageHighlight]
  );

  const onEdgeMouseLeave = useCallback(() => {
    onMessageHighlight?.(undefined);
  }, [onMessageHighlight]);

  const onEdgeClick = useCallback(
    (_, edge) => {
      onMessageSelect?.(edge.id);
    },
    [onMessageSelect]
  );

  return (
    <div className="h-48 w-full bg-gray-50 rounded-lg border border-gray-200">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onEdgeMouseEnter={onEdgeMouseEnter}
        onEdgeMouseLeave={onEdgeMouseLeave}
        onEdgeClick={onEdgeClick}
        fitView
        className="bg-gray-50"
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default AgentFlowDiagram;
