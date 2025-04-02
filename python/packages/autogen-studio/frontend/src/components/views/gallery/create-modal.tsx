import React, { useState, useRef } from "react";
import { Modal, Tabs, Input, Button, Alert, Upload } from "antd";
import { Globe, Upload as UploadIcon, Code } from "lucide-react";
import { MonacoEditor } from "../monaco";
import type { InputRef, UploadFile, UploadProps } from "antd";
import { defaultGallery } from "./utils";
import { Gallery, GalleryConfig } from "../../types/datamodel";

interface GalleryCreateModalProps {
  open: boolean;
  onCancel: () => void;
  onCreateGallery: (gallery: Gallery) => void;
}

export const GalleryCreateModal: React.FC<GalleryCreateModalProps> = ({
  open,
  onCancel,
  onCreateGallery,
}) => {
  const [activeTab, setActiveTab] = useState("url");
  const [url, setUrl] = useState("");
  const [jsonContent, setJsonContent] = useState(
    JSON.stringify(defaultGallery, null, 2)
  );
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const editorRef = useRef(null);

  const handleUrlImport = async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(url);
      const data = (await response.json()) as GalleryConfig;
      // TODO: Validate against Gallery schema
      onCreateGallery({
        config: data,
      });
      onCancel();
    } catch (err) {
      setError("Failed to fetch or parse gallery from URL");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = (info: { file: UploadFile }) => {
    const { status, originFileObj } = info.file;
    if (status === "done" && originFileObj instanceof File) {
      const reader = new FileReader();
      reader.onload = (e: ProgressEvent<FileReader>) => {
        try {
          const content = JSON.parse(
            e.target?.result as string
          ) as GalleryConfig;

          // TODO: Validate against Gallery schema
          onCreateGallery({
            config: content,
          });
          onCancel();
        } catch (err) {
          setError("Invalid JSON file");
        }
      };
      reader.readAsText(originFileObj);
    } else if (status === "error") {
      setError("File upload failed");
    }
  };

  const handlePasteImport = () => {
    try {
      const content = JSON.parse(jsonContent) as GalleryConfig;
      // TODO: Validate against Gallery schema
      onCreateGallery({
        config: content,
      });
      onCancel();
    } catch (err) {
      setError("Invalid JSON format");
    }
  };

  const uploadProps: UploadProps = {
    accept: ".json",
    showUploadList: false,
    customRequest: ({ file, onSuccess }) => {
      setTimeout(() => {
        onSuccess && onSuccess("ok");
      }, 0);
    },
    onChange: handleFileUpload,
  };

  const inputRef = useRef<InputRef>(null);

  const items = [
    {
      key: "url",
      label: (
        <span className="flex items-center gap-2">
          <Globe className="w-4 h-4" /> URL Import
        </span>
      ),
      children: (
        <div className="space-y-4">
          <Input
            ref={inputRef}
            placeholder="Enter gallery URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <div className="text-xs">
            Sample
            <a
              role="button"
              onClick={(e) => {
                setUrl(
                  "https://raw.githubusercontent.com/victordibia/multiagent-systems-with-autogen/refs/heads/main/research/components/gallery/base.json"
                );
                e.preventDefault();
              }}
              href="https://raw.githubusercontent.com/victordibia/multiagent-systems-with-autogen/refs/heads/main/research/components/gallery/base.json"
              target="_blank"
              rel="noreferrer"
              className="text-accent"
            >
              {" "}
              gallery.json{" "}
            </a>
          </div>
          <Button
            type="primary"
            onClick={handleUrlImport}
            disabled={!url || isLoading}
            block
          >
            Import from URL
          </Button>
        </div>
      ),
    },
    {
      key: "file",
      label: (
        <span className="flex items-center gap-2">
          <UploadIcon className="w-4 h-4" /> File Upload
        </span>
      ),
      children: (
        <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-4">
          <Upload.Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <UploadIcon className="w-8 h-8 mx-auto text-secondary" />
            </p>
            <p className="ant-upload-text">
              Click or drag JSON file to this area
            </p>
          </Upload.Dragger>
        </div>
      ),
    },
    {
      key: "paste",
      label: (
        <span className="flex items-center gap-2">
          <Code className="w-4 h-4" /> Paste JSON
        </span>
      ),
      children: (
        <div className="space-y-4">
          <div className="h-64">
            <MonacoEditor
              value={jsonContent}
              onChange={setJsonContent}
              editorRef={editorRef}
              language="json"
              minimap={false}
            />
          </div>
          <Button type="primary" onClick={handlePasteImport} block>
            Import JSON
          </Button>
        </div>
      ),
    },
  ];

  return (
    <Modal
      title="Create New Gallery"
      open={open}
      onCancel={onCancel}
      footer={null}
      width={800}
    >
      <div className="mt-4">
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={items} />

        {error && (
          <Alert message={error} type="error" showIcon className="mt-4" />
        )}
      </div>
    </Modal>
  );
};

export default GalleryCreateModal;
