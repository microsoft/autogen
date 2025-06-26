import React, { useState, useCallback, useEffect } from "react";
import {
  Button,
  Typography,
  Space,
  Alert,
  Spin,
  Card,
  List,
  Tag,
  Divider,
} from "antd";
import { Package, Eye, Download } from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { mcpAPI } from "../../../../../mcp/api";

const { Text, Title } = Typography;

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
}

export const McpResourcesTab: React.FC<McpResourcesTabProps> = ({
  serverParams,
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

  const handleListResources = useCallback(async () => {
    setLoadingResources(true);
    setError(null);

    try {
      const result = await mcpAPI.listResources(serverParams);

      if (result.status) {
        setResources(result.resources || []);
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Failed to fetch resources: ${err.message}`);
    } finally {
      setLoadingResources(false);
    }
  }, [serverParams]);

  const handleGetResource = useCallback(
    async (resource: Resource) => {
      setLoadingContent(true);
      setError(null);
      setSelectedResource(resource);

      try {
        const result = await mcpAPI.getResource(serverParams, resource.uri);

        if (result.status) {
          setResourceContent(result.contents || []);
        } else {
          setError(result.message);
        }
      } catch (err: any) {
        setError(`Failed to get resource: ${err.message}`);
      } finally {
        setLoadingContent(false);
      }
    },
    [serverParams]
  );

  // Load resources on mount
  useEffect(() => {
    handleListResources();
  }, [handleListResources]);

  const renderResourcesList = () => (
    <Card size="small" title="Available Resources">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Button
          type="primary"
          onClick={handleListResources}
          loading={loadingResources}
          icon={<Package size={16} />}
        >
          {resources.length > 0 ? "Refresh Resources" : "Load Resources"}
        </Button>

        {resources.length > 0 ? (
          <List
            size="small"
            dataSource={resources}
            renderItem={(resource) => (
              <List.Item
                actions={[
                  <Button
                    key="view"
                    type="link"
                    size="small"
                    icon={<Eye size={14} />}
                    onClick={() => handleGetResource(resource)}
                    loading={
                      loadingContent && selectedResource?.uri === resource.uri
                    }
                  >
                    View
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{resource.name || resource.uri}</Text>
                      {resource.mimeType && (
                        <Tag color="blue">{resource.mimeType}</Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size="small">
                      {resource.description && (
                        <Text type="secondary">{resource.description}</Text>
                      )}
                      <Text code style={{ fontSize: "11px" }}>
                        {resource.uri}
                      </Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          !loadingResources && <Text type="secondary">No resources found</Text>
        )}

        {resources.length > 0 && (
          <Text type="secondary">Found {resources.length} resource(s)</Text>
        )}
      </Space>
    </Card>
  );

  const renderResourceContent = () => {
    if (!selectedResource || !resourceContent) return null;

    return (
      <Card
        size="small"
        title={
          <Space>
            <Eye size={16} />
            Resource Content: {selectedResource.name || selectedResource.uri}
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          {resourceContent.map((content, index) => (
            <Card
              key={index}
              size="small"
              style={{ backgroundColor: "#f9f9f9" }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                <Space>
                  <Tag color="green">{content.type}</Tag>
                  {content.mimeType && (
                    <Tag color="blue">{content.mimeType}</Tag>
                  )}
                </Space>

                {content.text && (
                  <div>
                    <Text strong>Content:</Text>
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        margin: "8px 0 0 0",
                        maxHeight: "400px",
                        overflow: "auto",
                        background: "white",
                        padding: "8px",
                        border: "1px solid #d9d9d9",
                        borderRadius: "4px",
                      }}
                    >
                      {content.text}
                    </pre>
                  </div>
                )}

                {content.blob && (
                  <div>
                    <Text strong>Binary Data:</Text>
                    <div
                      style={{
                        margin: "8px 0 0 0",
                        padding: "8px",
                        background: "white",
                        border: "1px solid #d9d9d9",
                        borderRadius: "4px",
                      }}
                    >
                      <Space>
                        <Download size={16} />
                        <Text type="secondary">
                          Binary content ({content.blob.length} characters)
                        </Text>
                        {content.mimeType?.startsWith("image/") && (
                          <Tag color="orange">Image</Tag>
                        )}
                      </Space>
                    </div>
                  </div>
                )}
              </Space>
            </Card>
          ))}
        </Space>
      </Card>
    );
  };

  if (error) {
    return (
      <Alert
        type="error"
        message="Resources Error"
        description={error}
        action={
          <Button
            size="small"
            onClick={handleListResources}
            loading={loadingResources}
          >
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      {renderResourcesList()}
      {selectedResource && resourceContent && (
        <>
          <Divider />
          {renderResourceContent()}
        </>
      )}
    </Space>
  );
};
