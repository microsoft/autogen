// edgemessagemodal.tsx
import React, { useState, useMemo } from "react";
import { Modal, Input } from "antd";
import { RenderMessage } from "../rendermessage";
import { CustomEdge } from "./edge";

const { Search } = Input;

interface EdgeMessageModalProps {
  open: boolean;
  onClose: () => void;
  edge: CustomEdge | null;
}

export const EdgeMessageModal: React.FC<EdgeMessageModalProps> = ({
  open,
  onClose,
  edge,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const totalTokens = useMemo(() => {
    if (!edge?.data?.messages) return 0;
    return edge.data.messages.reduce((acc, msg) => {
      const promptTokens = msg.models_usage?.prompt_tokens || 0;
      const completionTokens = msg.models_usage?.completion_tokens || 0;
      return acc + promptTokens + completionTokens;
    }, 0);
  }, [edge?.data?.messages]);

  const filteredMessages = useMemo(() => {
    if (!edge?.data?.messages) return [];
    if (!searchTerm) return edge.data.messages;

    return edge.data.messages.filter(
      (msg) =>
        typeof msg.content === "string" &&
        msg.content.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [edge?.data?.messages, searchTerm]);

  if (!edge) return null;

  return (
    <Modal
      title={
        <div className="space-y-2">
          <div className="font-medium">
            {edge.source} → {edge.target}
          </div>
          <div className="text-sm text-secondary flex justify-between">
            {edge.data && (
              <span>
                {edge.data.messages.length} message
                {`${edge.data.messages.length > 1 ? "s" : ""}`}
              </span>
            )}
            <span>{totalTokens.toLocaleString()} tokens</span>
          </div>
          {edge.data && edge.data.messages.length > 0 && (
            <div className="text-xs py-2 font-normal">
              {" "}
              The above represents the number of times the {`${edge.target}`}{" "}
              node sent a message{" "}
              <span className="font-semibold underline text-accent">after</span>{" "}
              the {`${edge.source}`} node.{" "}
            </div>
          )}
        </div>
      }
      open={open}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <div className="max-h-[70vh] overflow-y-auto space-y-4 scroll pr-2">
        <Search
          placeholder="Search message content..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          allowClear
          className="sticky top-0 z-10"
        />

        <div className="space-y-4 ">
          {filteredMessages.map((msg, idx) => (
            <RenderMessage
              key={idx}
              message={msg}
              isLast={idx === filteredMessages.length - 1}
            />
          ))}

          {filteredMessages.length === 0 && (
            <div className="text-center text-secondary py-8">
              No messages found
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
