import React, { useState } from "react";
import Editor from "@monaco-editor/react";

export const MonacoEditor = ({
  value,
  editorRef,
  language,
  onChange,
  minimap = true,
  className,
}: {
  value: string;
  onChange?: (value: string) => void;
  editorRef: any;
  language: string;
  minimap?: boolean;
  className?: string;
}) => {
  const [isEditorReady, setIsEditorReady] = useState(false);
  const onEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    setIsEditorReady(true);
  };
  return (
    <div id="monaco-editor" className={`h-full rounded ${className}`}>
      <Editor
        height="100%"
        className="h-full rounded"
        defaultLanguage={language}
        defaultValue={value}
        value={value}
        onChange={(value: string | undefined) => {
          if (onChange && value) {
            onChange(value);
          }
        }}
        onMount={onEditorDidMount}
        theme="vs-dark"
        options={{
          wordWrap: "on",
          wrappingIndent: "indent",
          wrappingStrategy: "advanced",
          minimap: {
            enabled: minimap,
          },
        }}
      />
    </div>
  );
};
