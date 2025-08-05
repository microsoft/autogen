import React, { useState, useEffect } from "react";
import { ChevronRight, TriangleAlert } from "lucide-react";
import { LabsSidebar } from "./sidebar";
import { Lab, defaultLabs } from "./types";
import { LabContent } from "./labs/guides";

export const LabsManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [labs, setLabs] = useState<Lab[]>([]);
  const [currentLab, setcurrentLab] = useState<Lab | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("labsSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("labsSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  // Set first guide as current if none selected
  useEffect(() => {
    if (!currentLab && labs.length > 0) {
      setcurrentLab(labs[0]);
    }
  }, [labs, currentLab]);

  useEffect(() => {
    setLabs(defaultLabs);
  }, []);

  return (
    <div className="relative    flex h-full w-full">
      {/* Sidebar */}
      <div
        className={`absolute  left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <LabsSidebar
          isOpen={isSidebarOpen}
          labs={labs}
          currentLab={currentLab}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectLab={setcurrentLab}
          isLoading={isLoading}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all max-w-5xl  -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Labs</span>
            {currentLab && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">{currentLab.title}</span>
              </>
            )}
          </div>
          <div className="rounded border border-secondary border-dashed p-2 text-sm mb-4">
            <TriangleAlert className="w-4 h-4 inline-block mr-2 -mt-1 text-secondary " />{" "}
            Labs is designed to host experimental features for building and
            debugging multiagent applications.
          </div>
          {/* Content Area */}
          {currentLab ? (
            <LabContent lab={currentLab} />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-190px)] text-secondary">
              Select a lab from the sidebar to get started
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LabsManager;
