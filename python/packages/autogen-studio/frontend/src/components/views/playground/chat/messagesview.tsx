"use client";
import MarkdownView from "../markdown";

function isString(content: any) {
  return typeof content === "string" || content instanceof String;
}

export default function AgentMessagesView({ messages }: { messages: any }) {
  // console.log('metadata', metadata);
  const messagesView = (messages || []).map((message: any, i: number) => {
    const bg = i % 2 === 0 ? "bg-primary" : "bg-secondary";
    const contentIsString = isString(message.content);
    return (
      <div key={"messagerow" + i}>
        <div className={`text-xs border rounded p-2 mb-2 ${bg}`}>
          <div>{message?.source}</div>
          {contentIsString && <MarkdownView data={message.content} />}
          {/* {!contentIsString && <AgentMessagesView messages={message.content} />} */}
        </div>
      </div>
    );
  });
  return (
    <div className=" overflow-x-hidden overflow-y-auto h-full scroll">
      {" "}
      <div className="mb-2 text-xs">
        The agent workflow generated {messagesView.length} message
        {messagesView.length > 1 ? "s" : ""}{" "}
      </div>
      <div>{messagesView}</div>
    </div>
  );
}
