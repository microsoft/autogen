import React, { useState, useEffect } from "react";
import { ChevronRight, TriangleAlert } from "lucide-react";
import { DeploySidebar } from "./sidebar";
import { Guide, defaultGuides } from "./types";
import { GuideContent } from "./guides/guides";

export const DeployManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [guides, setGuides] = useState<Guide[]>(defaultGuides);
  const [currentGuide, setCurrentGuide] = useState<Guide | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("deploySidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("deploySidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  // Set first guide as current if none selected
  useEffect(() => {
    if (!currentGuide && guides.length > 0) {
      setCurrentGuide(guides[0]);
    }
  }, [guides, currentGuide]);

  return (
    <div className="relative    flex h-full w-full">
      {/* Sidebar */}
      <div
        className={`absolute  left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <DeploySidebar
          isOpen={isSidebarOpen}
          guides={guides}
          currentGuide={currentGuide}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectGuide={setCurrentGuide}
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
            <span className="text-primary font-medium">Deploy</span>
            {currentGuide && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">{currentGuide.title}</span>
              </>
            )}
          </div>
          <div className="rounded border border-secondary border-dashed p-2 text-sm mb-4">
            <TriangleAlert className="w-4 h-4 inline-block mr-2 -mt-1 text-secondary " />{" "}
            The deployment guide section is work in progress.
          </div>
          {/* Content Area */}
          {currentGuide ? (
            <GuideContent guide={currentGuide} />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-190px)] text-secondary">
              Select a guide from the sidebar to get started
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DeployManager;
