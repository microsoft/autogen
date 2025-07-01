import React, { useState, useCallback, useEffect, useRef } from "react";
import { Button, Typography, Space, Alert, Spin } from "antd";
import {
  Package,
  Eye,
  Download,
  RotateCcw,
  FileText,
  Hash,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { McpWebSocketClient, ServerCapabilities } from "../../../../../mcp/api";

const { Text } = Typography;

interface Resource {
  uri: string;
  name?: string;
  description?: string;
  mimeType?: string;
}

interface ResourceContent {
  type: string;
  text?: string;
  blob?: string;
  mimeType?: string;
}

interface McpResourcesTabProps {
  serverParams: McpServerParams;
  wsClient: McpWebSocketClient | null;
  connected: boolean;
  capabilities: ServerCapabilities | null;
}

export const McpResourcesTab: React.FC<McpResourcesTabProps> = ({
  serverParams,
  wsClient,
  connected,
  capabilities,
}) => {
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedResource, setSelectedResource] = useState<Resource | null>(
    null
  );
  const [resourceContent, setResourceContent] = useState<
    ResourceContent[] | null
  >(null);
  const [loadingResources, setLoadingResources] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const resourceContentRef = useRef<HTMLDivElement>(null);

  const handleListResources = useCallback(async () => {
    if (!connected || !wsClient) {
      setLoadingError("WebSocket not connected");
      return;
    }

    setLoadingResources(true);
    setLoadingError(null);

    try {
      const result = await wsClient.executeOperation({
        operation: "list_resources",
      });

      if (result?.resources) {
        setResources(result.resources);
      } else {
        setLoadingError("No resources received from server");
      }
    } catch (err: any) {
      setLoadingError(
        `Failed to fetch resources: ${err.message || "Unknown error"}`
      );
    } finally {
      setLoadingResources(false);
    }
  }, [connected, wsClient]);

  const handleGetResource = useCallback(
    async (resource: Resource) => {
      if (!connected || !wsClient) return;

      setLoadingContent(true);
      setError(null);
      setSelectedResource(resource);

      try {
        const result = await wsClient.executeOperation({
          operation: "read_resource",
          uri: resource.uri,
        });

        if (result?.contents) {
          setResourceContent(result.contents);
        } else {
          setError("No content received from resource");
        }
      } catch (err: any) {
        setError(`Failed to get resource: ${err.message || "Unknown error"}`);
      } finally {
        setLoadingContent(false);
      }
    },
    [connected, wsClient]
  );

  // Load resources when connected and capabilities indicate resources are available
  useEffect(() => {
    if (connected && capabilities?.resources) {
      handleListResources();
    }
  }, [connected, capabilities?.resources, handleListResources]);

  // Auto-scroll to resource content when it appears
  useEffect(() => {
    if (resourceContent && resourceContentRef.current) {
      setTimeout(() => {
        resourceContentRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 100);
    }
  }, [resourceContent]);

  const renderResourcesList = () => (
    <div className="bg-secondary rounded-lg border border-tertiary p-4">
      <div className="flex items-center gap-2 mb-4">
        <Package size={18} className="text-primary" />
        <h3 className="text-lg font-semibold text-primary m-0">
          Available Resources
        </h3>
      </div>

      <div className="space-y-4">
        <Button
          type="primary"
          onClick={handleListResources}
          loading={loadingResources}
          icon={<Package size={16} />}
          className="flex items-center gap-2"
        >
          {resources.length > 0 ? "Refresh Resources" : "Load Resources"}
        </Button>

        {loadingError && (
          <Alert
            type="error"
            message="Failed to Load Resources"
            description={loadingError}
            action={
              <Space>
                <Button
                  size="small"
                  onClick={handleListResources}
                  loading={loadingResources}
                >
                  Retry
                </Button>
                <Button size="small" onClick={() => setLoadingError(null)}>
                  Clear
                </Button>
              </Space>
            }
            showIcon
          />
        )}

        {resources.length > 0 ? (
          <div className="space-y-3">
            {resources.map((resource, index) => (
              <div
                key={resource.uri}
                className="bg-primary border border-tertiary rounded-md p-3 hover:border-accent transition-colors"
              >
                <div className="flex justify-between items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Text className="font-medium text-primary truncate">
                        {resource.name || resource.uri}
                      </Text>
                      {resource.mimeType && (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                          {resource.mimeType}
                        </span>
                      )}
                    </div>

                    {resource.description && (
                      <Text className="text-secondary text-sm mb-2 block">
                        {resource.description}
                      </Text>
                    )}

                    <div className="bg-tertiary rounded px-2 py-1">
                      <Text className="text-xs font-mono text-secondary break-all">
                        {resource.uri}
                      </Text>
                    </div>
                  </div>

                  <Button
                    type="text"
                    size="small"
                    icon={<Eye size={14} />}
                    onClick={() => handleGetResource(resource)}
                    loading={
                      loadingContent && selectedResource?.uri === resource.uri
                    }
                    className="flex items-center gap-1 text-accent hover:text-accent-dark hover:bg-accent/10"
                  >
                    View
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          !loadingResources && (
            <Text className="text-secondary text-center block py-4">
              No resources found
            </Text>
          )
        )}

        {resources.length > 0 && (
          <Text className="text-secondary text-sm">
            Found {resources.length} resource(s)
          </Text>
        )}
      </div>
    </div>
  );

  const renderResourceContent = () => {
    if (!selectedResource || !resourceContent) return null;

    return (
      <div
        ref={resourceContentRef}
        className="bg-secondary rounded-lg border border-tertiary p-4"
      >
        <div className="flex items-center gap-2 mb-4">
          <Eye size={18} className="text-primary" />
          <h3 className="text-lg font-semibold text-primary m-0">
            Resource Content: {selectedResource.name || selectedResource.uri}
          </h3>
        </div>

        <div className="space-y-4">
          {resourceContent.map((content, index) => (
            <div
              key={index}
              className="bg-primary border border-tertiary rounded-lg p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2.5 py-1 text-sm font-medium bg-green-100 text-green-800 rounded-full">
                  {content.type}
                </span>
                {content.mimeType && (
                  <span className="inline-flex items-center px-2.5 py-1 text-sm font-medium bg-blue-100 text-blue-800 rounded-full">
                    {content.mimeType}
                  </span>
                )}
              </div>

              {content.text && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <FileText size={16} className="text-primary" />
                    <Text className="font-medium text-primary">Content:</Text>
                  </div>
                  <pre className="whitespace-pre-wrap bg-tertiary border border-tertiary rounded-md p-3 text-sm text-primary overflow-auto max-h-96 font-mono">
                    {content.text}
                  </pre>
                </div>
              )}

              {content.blob && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Download size={16} className="text-primary" />
                    <Text className="font-medium text-primary">
                      Binary Data:
                    </Text>
                  </div>
                  <div className="bg-tertiary border border-tertiary rounded-md p-3">
                    <div className="flex items-center gap-2 text-secondary">
                      <Download size={16} />
                      <Text className="text-secondary">
                        Binary content ({content.blob.length} characters)
                      </Text>
                      {content.mimeType?.startsWith("image/") && (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded-full ml-2">
                          Image
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="mt-4 space-y-6 h-full overflow-auto">
      {renderResourcesList()}
      {selectedResource && resourceContent && !loadingError && (
        <>
          <div className="border-t border-tertiary" />
          {renderResourceContent()}
        </>
      )}
      {error && (
        <Alert
          type="error"
          message="Resource Operation Error"
          description={error}
          action={
            <Space>
              <Button size="small" onClick={() => setError(null)}>
                Clear Error
              </Button>
              <Button
                size="small"
                onClick={handleListResources}
                loading={loadingResources}
              >
                Retry
              </Button>
            </Space>
          }
          showIcon
        />
      )}
    </div>
  );
};
