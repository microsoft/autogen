import React from "react";
import { Copy } from "lucide-react";
import { Guide } from "../types";
import PythonGuide from "./python";
import DockerGuide from "./docker";

import { MonacoEditor } from "../../monaco";

interface GuideContentProps {
  guide: Guide;
}

export const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text);
};
export const GuideContent: React.FC<GuideContentProps> = ({ guide }) => {
  // Render different content based on guide type and id
  switch (guide.id) {
    case "python-setup":
      return <PythonGuide />;

    case "docker-setup":
      return <DockerGuide />;

    // Add more cases for other guides...

    default:
      return (
        <div className="text-secondary">
          A Guide with the title <strong>{guide.title}</strong> is work in
          progress!
        </div>
      );
  }
};

interface CodeSectionProps {
  title: string;
  description?: string | React.ReactNode;
  code?: string;
  onCopy: (text: string) => void;
  language?: string;
}

const editorRef = React.createRef<any>();

export const CodeSection: React.FC<CodeSectionProps> = ({
  title,
  description,
  code,
  onCopy,
  language = "python",
}) => (
  <section className="mt-6 bg-seco">
    <h2 className="text-md font-semibold mb-3">{title}</h2>
    {description && <div className="  mb-3">{description}</div>}
    {code && (
      <div className="relative bg-secondary text-sm p-4 rounded overflow-auto scroll h-72">
        <MonacoEditor language={language} editorRef={editorRef} value={code} />
        <button
          onClick={() => onCopy(code)}
          className="absolute right-2 top-2 p-2  bg-secondary hover:bg-primary rounded-md"
        >
          <Copy className="w-4 h-4 hover:text-accent transition duration-100" />
        </button>
      </div>
    )}
  </section>
);

export default GuideContent;
