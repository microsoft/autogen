import React, { useState, useRef } from "react";
import { Button, message, Tooltip } from "antd";
import {
  Package,
  Users,
  Bot,
  Globe,
  RefreshCw,
  Edit2,
  X,
  Wrench,
  Brain,
  Timer,
  Save,
} from "lucide-react";
import type { Gallery } from "./types";
import { useGalleryStore } from "./store";
import { MonacoEditor } from "../monaco";

interface GalleryDetailProps {
  gallery: Gallery;
  onSave: (updates: Partial<Gallery>) => void;
  onDirtyStateChange: (isDirty: boolean) => void;
}

export const GalleryDetail: React.FC<GalleryDetailProps> = ({
  gallery,
  onSave,
  onDirtyStateChange,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [jsonValue, setJsonValue] = useState(JSON.stringify(gallery, null, 2));
  const editorRef = useRef(null);
  const { syncGallery, getLastSyncTime } = useGalleryStore();

  const handleSync = async () => {
    if (!gallery.url) return;

    setIsSyncing(true);
    try {
      await syncGallery(gallery.id);
      message.success("Gallery synced successfully");
    } catch (error) {
      message.error("Failed to sync gallery");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleJsonChange = (value: string) => {
    setJsonValue(value);
    onDirtyStateChange(true);
  };

  const handleSave = async () => {
    try {
      const parsedGallery = JSON.parse(jsonValue);
      const updatedGallery = {
        ...parsedGallery,
        id: gallery.id,
        metadata: {
          ...parsedGallery.metadata,
          updated_at: new Date().toISOString(),
        },
      };
      await onSave(updatedGallery);
      onDirtyStateChange(false);
      setIsEditing(false);
      message.success("Gallery updated successfully");
    } catch (error) {
      message.error("Invalid JSON format");
    }
  };

  const stats = [
    {
      icon: <Users className="w-4 h-4" />,
      title: "team",
      count: gallery.items.teams.length,
    },
    {
      icon: <Bot className="w-4 h-4" />,
      title: "agent",
      count: gallery.items.components.agents.length,
    },
    {
      icon: <Wrench className="w-4 h-4" />,
      title: "tool",
      count: gallery.items.components.tools.length,
    },
    {
      icon: <Brain className="w-4 h-4" />,
      title: "model",
      count: gallery.items.components.models.length,
    },
    {
      icon: <Timer className="w-4 h-4" />,
      title: "termination",
      count: gallery.items.components.terminations.length,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Banner Section */}
      <div className="relative h-72 rounded bg-secondary overflow-hidden">
        <img
          src="/images/bg/layeredbg.svg"
          alt="Gallery Banner"
          className="absolute w-full h-full object-cover"
        />
        <div className="relative z-10 p-6 h-full flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-medium text-primary">
                {gallery.name}
              </h1>
              {gallery.url && (
                <Tooltip title="Remote Gallery">
                  <Globe className="w-5 h-5 text-secondary" />
                </Tooltip>
              )}
            </div>
            <p className="text-secondary w-1/2 mt-2 line-clamp-3">
              {gallery.metadata.description}
            </p>
            <p className="text-secondary text-sm mt-2">
              {gallery.metadata.author}
            </p>
          </div>

          <div className="flex gap-2">
            <div className="bg-tertiary backdrop-blur rounded p-2 flex items-center gap-2">
              <Package className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                {Object.values(gallery.items.components).reduce(
                  (sum, arr) => sum + arr.length,
                  0
                )}{" "}
                components
              </span>
            </div>
            <div className="bg-tertiary backdrop-blur rounded p-2 text-sm">
              v{gallery.metadata.version}
            </div>
            {gallery.metadata.tags?.map((tag) => (
              <div
                key={tag}
                className="bg-tertiary backdrop-blur rounded p-2 px-2 text-sm"
              >
                {tag}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Actions Bar */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2 items-center">
          <div className="text-sm text-gray-600 flex flex-wrap gap-x-6 gap-y-2">
            {stats.map(({ icon, title, count }) => (
              <div key={title} className="flex items-center gap-2">
                <span className="text-gray-500">{icon}</span>
                <span>
                  {count} {count === 1 ? title : `${title}s`}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          {gallery.url && (
            <Tooltip
              title={
                getLastSyncTime(gallery.id)
                  ? `Last synced: ${getLastSyncTime(gallery.id)}`
                  : "Never synced"
              }
            >
              <Button
                icon={<RefreshCw className={isSyncing ? "animate-spin" : ""} />}
                loading={isSyncing}
                onClick={handleSync}
              >
                Sync
              </Button>
            </Tooltip>
          )}
          {!isEditing ? (
            <Button
              icon={<Edit2 className="w-4 h-4" />}
              onClick={() => setIsEditing(true)}
            >
              Edit
            </Button>
          ) : (
            <>
              <Button
                icon={<X className="w-4 h-4" />}
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </Button>
              <Button type="primary" onClick={handleSave}>
                Save Changes
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Editor Section */}
      {isEditing && (
        <div
          className="fixed bottom-0 left-0 right-0 bg-primary z-50 shadow-lg transition-transform duration-300 ease-in-out transform"
          style={{ height: "70vh" }}
        >
          <div className="border-b border-secondary p-4 flex justify-between items-center">
            <h3 className="text-normal font-medium">
              Edit Gallery Configuration
            </h3>
            <div className="inline-flex gap-2">
              {/* <Button
                icon={<RefreshCw className="w-4 h-4 " />}
                onClick={handleSync}
              ></Button> */}
              <Tooltip title="Save Changes">
                <Button
                  icon={<Save className="w-4 h-4 " />}
                  onClick={handleSave}
                ></Button>
              </Tooltip>
              <Tooltip title="Cancel Editing">
                <Button
                  icon={<X className="w-4 h-4" />}
                  onClick={() => setIsEditing(false)}
                />
              </Tooltip>
            </div>
          </div>
          <div className="h-[calc(100%-60px)]">
            <MonacoEditor
              value={jsonValue}
              onChange={handleJsonChange}
              editorRef={editorRef}
              language="json"
              minimap={true}
            />
          </div>
        </div>
      )}
    </div>
  );
};
