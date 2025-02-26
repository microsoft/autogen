import React from "react";
import { AlertTriangle, XCircle, X } from "lucide-react";
import { Tooltip } from "antd";
import { ValidationResponse } from "../api";

interface ValidationErrorViewProps {
  validation: ValidationResponse;
  onClose: () => void;
}

const ValidationErrorView: React.FC<ValidationErrorViewProps> = ({
  validation,
  onClose,
}) => (
  <div
    style={{ zIndex: 1000 }}
    className="fixed inset-0 bg-black/80  flex items-center justify-center transition-opacity duration-300"
    onClick={onClose}
  >
    <div
      className="relative bg-primary w-full h-full md:w-4/5 md:h-4/5 md:rounded-lg p-8 overflow-auto"
      style={{ opacity: 0.95 }}
      onClick={(e) => e.stopPropagation()}
    >
      <Tooltip title="Close">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-tertiary  hover:bg-secondary text-primary transition-colors"
        >
          <X size={24} />
        </button>
      </Tooltip>

      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <XCircle size={20} className="text-red-500" />
          <h3 className="text-lg font-medium">Validation Issues</h3>
          <h4 className="text-sm text-secondary">
            {validation.errors.length} errors • {validation.warnings.length}{" "}
            warnings
          </h4>
        </div>

        {/* Errors Section */}
        {validation.errors.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Errors</h4>
            {validation.errors.map((error, idx) => (
              <div key={idx} className="p-4 bg-tertiary rounded-lg">
                <div className="flex gap-3">
                  <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-1" />
                  <div>
                    <div className="text-xs font-medium uppercase text-secondary mb-1">
                      {error.field}
                    </div>
                    <div className="text-sm">{error.error}</div>
                    {error.suggestion && (
                      <div className="text-sm mt-2 text-secondary">
                        Suggestion: {error.suggestion}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Warnings Section */}
        {validation.warnings.length > 0 && (
          <div className="space-y-2 mt-6">
            <h4 className="text-sm font-medium">Warnings</h4>
            {validation.warnings.map((warning, idx) => (
              <div key={idx} className="p-4 bg-tertiary rounded-lg">
                <div className="flex gap-3">
                  <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0 mt-1" />
                  <div>
                    <div className="text-xs font-medium uppercase text-secondary mb-1">
                      {warning.field}
                    </div>
                    <div className="text-sm">{warning.error}</div>
                    {warning.suggestion && (
                      <div className="text-sm mt-2 text-secondary">
                        Suggestion: {warning.suggestion}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  </div>
);

interface ValidationErrorsProps {
  validation: ValidationResponse;
}

export const ValidationErrors: React.FC<ValidationErrorsProps> = ({
  validation,
}) => {
  const [showFullView, setShowFullView] = React.useState(false);

  return (
    <>
      <div
        className="flex items-center gap-2 py-2   px-3 bg-secondary rounded  text-sm text-secondary hover:text-primary transition-colors group cursor-pointer"
        onClick={() => setShowFullView(true)}
      >
        <XCircle size={14} className="text-red-500" />
        <span className="flex-1">
          {validation.errors.length} errors • {validation.warnings.length}{" "}
          warnings
        </span>
        <AlertTriangle size={14} className="group-hover:text-accent" />
      </div>

      {showFullView && (
        <ValidationErrorView
          validation={validation}
          onClose={() => setShowFullView(false)}
        />
      )}
    </>
  );
};
