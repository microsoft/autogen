import React from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Terminal,
  XCircle,
  CheckCircle,
} from "lucide-react";
import { ComponentTestResult } from "../../api";

interface TestDetailsProps {
  result: ComponentTestResult;
  onClose: () => void;
}

const TestDetails: React.FC<TestDetailsProps> = ({ result, onClose }) => {
  const [isExpanded, setIsExpanded] = React.useState(false);

  const statusColor = result.status ? " border-green-200" : "  border-red-200";
  const iconColor = result.status ? "text-green-500" : "text-red-500";

  return (
    <div
      className={`mb-6 rounded-lg border text-primary ${statusColor} overflow-hidden`}
    >
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {result.status ? (
              <CheckCircle className={`w-5 h-5 ${iconColor}`} />
            ) : (
              <AlertCircle className={`w-5 h-5 ${iconColor}`} />
            )}
            <span className="font-medium text-primary">{result.message}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-black/5 rounded-md"
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-black/5 rounded-md"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        </div>

        {isExpanded && result.logs && result.logs.length > 0 && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4" />
              <span className="text-sm font-medium">Execution Logs</span>
            </div>
            <pre className="bg-secondary text-primary p-4 rounded-md text-sm font-mono overflow-x-auto">
              {result.logs.join("\n")}
            </pre>
          </div>
        )}

        {isExpanded && result.data && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4" />
              <span className="text-sm font-medium">Additional Data</span>
            </div>
            <pre className="bg-secondary text-primary p-4 rounded-md text-sm font-mono overflow-x-auto">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default TestDetails;
