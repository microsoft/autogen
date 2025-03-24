import {
  PaperAirplaneIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import { IStatus } from "../../../types/app";
import { Upload, message, Button, Tooltip, notification } from "antd";
import type { UploadFile, UploadProps, RcFile } from "antd/es/upload/interface";
import {
  FileTextIcon,
  ImageIcon,
  Paperclip,
  UploadIcon,
  XIcon,
} from "lucide-react";

// Maximum file size in bytes (5MB)
const MAX_FILE_SIZE = 5 * 1024 * 1024;
// Allowed file types
const ALLOWED_FILE_TYPES = [
  "text/plain",
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/svg+xml",
];

// Threshold for large text files (in characters)
const LARGE_TEXT_THRESHOLD = 1000;

interface ChatInputProps {
  onSubmit: (text: string, files: RcFile[]) => void;
  loading: boolean;
  error: IStatus | null;
  disabled?: boolean;
}

export default function ChatInput({
  onSubmit,
  loading,
  error,
  disabled = false,
}: ChatInputProps) {
  const textAreaRef = React.useRef<HTMLTextAreaElement>(null);
  const [previousLoading, setPreviousLoading] = React.useState(loading);
  const [text, setText] = React.useState("What is the capital of France?");
  const [fileList, setFileList] = React.useState<UploadFile[]>([]);
  const [dragOver, setDragOver] = React.useState(false);
  const [notificationApi, notificationContextHolder] =
    notification.useNotification();

  const textAreaDefaultHeight = "64px";
  const isInputDisabled = disabled || loading;

  // Handle textarea auto-resize
  React.useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.style.height = textAreaDefaultHeight;
      const scrollHeight = textAreaRef.current.scrollHeight;
      textAreaRef.current.style.height = `${scrollHeight}px`;
    }
  }, [text]);

  // Clear input when loading changes from true to false (meaning the response is complete)
  React.useEffect(() => {
    if (previousLoading && !loading && !error) {
      resetInput();
    }
    setPreviousLoading(loading);
  }, [loading, error, previousLoading]);

  // Add paste event listener
  React.useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (isInputDisabled) return;

      // Handle image paste
      if (e.clipboardData?.items) {
        let hasImageItem = false;

        for (let i = 0; i < e.clipboardData.items.length; i++) {
          const item = e.clipboardData.items[i];

          // Handle image items
          if (item.type.indexOf("image/") === 0) {
            hasImageItem = true;
            const file = item.getAsFile();

            if (file && file.size <= MAX_FILE_SIZE) {
              // Prevent the default paste behavior for images
              e.preventDefault();

              // Create a unique file name
              const fileName = `pasted-image-${new Date().getTime()}.png`;

              // Create a new File with a proper name
              const namedFile = new File([file], fileName, { type: file.type });

              // Convert to the expected UploadFile format
              const uploadFile: UploadFile = {
                uid: `paste-${Date.now()}`,
                name: fileName,
                status: "done",
                size: namedFile.size,
                type: namedFile.type,
                originFileObj: namedFile as RcFile,
              };

              // Add to file list
              setFileList((prev) => [...prev, uploadFile]);

              // Show successful paste notification
              message.success(`Image pasted successfully`);
            } else if (file && file.size > MAX_FILE_SIZE) {
              message.error(`Pasted image is too large. Maximum size is 5MB.`);
            }
          }

          // Handle text items - only if there's a large amount of text
          if (item.type === "text/plain" && !hasImageItem) {
            item.getAsString((text) => {
              // Only process for large text
              if (text.length > LARGE_TEXT_THRESHOLD) {
                notificationApi.info({
                  message: <span className="text-sm">Large Text Detected</span>,
                  description: (
                    <div>
                      <span className="text-sm text-secondary">
                        Would you like to convert this to a file attachment?
                      </span>
                      <div className="mt-2">
                        <Button
                          size="small"
                          onClick={() => {
                            // Create a text file from the pasted content
                            const blob = new Blob([text], {
                              type: "text/plain",
                            });
                            const file = new File(
                              [blob],
                              `pasted-text-${new Date().getTime()}.txt`,
                              { type: "text/plain" }
                            );

                            // Add to file list
                            const uploadFile: UploadFile = {
                              uid: `paste-${Date.now()}`,
                              name: file.name,
                              status: "done",
                              size: file.size,
                              type: file.type,
                              originFileObj: file as RcFile,
                            };

                            setFileList((prev) => [...prev, uploadFile]);
                            notificationApi.destroy(); // Close the notification
                          }}
                          type="primary"
                          className="mr-2"
                        >
                          Yes
                        </Button>
                        <Button
                          size="small"
                          onClick={() => {
                            notificationApi.destroy(); // Close the notification
                          }}
                        >
                          No
                        </Button>
                      </div>
                    </div>
                  ),
                  duration: 0, // Don't auto-close
                });
              }
            });
          }
        }
      }
    };

    // Add the paste event listener to the document
    document.addEventListener("paste", handlePaste);

    // Cleanup
    return () => {
      document.removeEventListener("paste", handlePaste);
    };
  }, [isInputDisabled, notificationApi]);

  const resetInput = () => {
    if (textAreaRef.current) {
      textAreaRef.current.value = "";
      textAreaRef.current.style.height = textAreaDefaultHeight;
      setText("");
      setFileList([]);
    }
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(event.target.value);
  };

  const handleSubmit = () => {
    if (
      (textAreaRef.current?.value || fileList.length > 0) &&
      !isInputDisabled
    ) {
      const query = textAreaRef.current?.value || "";

      // Get all valid RcFile objects
      const files = fileList
        .filter((file) => file.originFileObj)
        .map((file) => file.originFileObj as RcFile);

      onSubmit(query, files);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const uploadProps: UploadProps = {
    name: "file",
    multiple: true,
    fileList,
    beforeUpload: (file) => {
      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        message.error(`${file.name} is too large. Maximum size is 5MB.`);
        return Upload.LIST_IGNORE;
      }

      // Check file type
      if (!ALLOWED_FILE_TYPES.includes(file.type)) {
        notificationApi.warning({
          message: <span className="text-sm">Unsupported File Type</span>,
          description: (
            <span className="text-sm text-secondary">
              Please upload only text (.txt) or images (.jpg, .png, .gif, .svg)
              files.
            </span>
          ),
          showProgress: true,
          duration: 8.5,
        });
        return Upload.LIST_IGNORE;
      }

      // Correctly set the uploadFile with originFileObj property
      const uploadFile: UploadFile = {
        uid: file.uid,
        name: file.name,
        status: "done",
        size: file.size,
        type: file.type,
        originFileObj: file,
      };

      setFileList((prev) => [...prev, uploadFile]);
      return false; // Prevent automatic upload
    },
    onRemove: (file) => {
      setFileList(fileList.filter((item) => item.uid !== file.uid));
    },
    showUploadList: false, // We'll handle our own custom file preview
    customRequest: ({ onSuccess }) => {
      // Mock successful upload since we're not actually uploading anywhere yet
      if (onSuccess) onSuccess("ok");
    },
  };

  const getFileIcon = (file: UploadFile) => {
    const fileType = file.type || "";
    if (fileType.startsWith("image/")) {
      return <ImageIcon className="w-4 h-4" />;
    }
    return <FileTextIcon className="w-4 h-4" />;
  };

  return (
    <div className="mt-2 w-full">
      {notificationContextHolder}
      {/* File previews */}
      {fileList.length > 0 && (
        <div className="-mb-2 mx-1 bg-tertiary rounded-t border-b-0 p-2 flex bodrder flex-wrap gap-2">
          {fileList.map((file) => (
            <div
              key={file.uid}
              className="flex items-center gap-1 bg-secondary rounded px-2 py-1 text-xs"
            >
              {getFileIcon(file)}
              <span className="truncate max-w-[150px]">{file.name}</span>
              <Button
                type="text"
                size="small"
                className="p-0 ml-1 flex items-center justify-center"
                onClick={() =>
                  setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
                }
                icon={<XIcon className="w-3 h-3" />}
              />
            </div>
          ))}
        </div>
      )}

      <div
        className={`mt-2 rounded shadow-sm flex mb-1 ${
          isInputDisabled ? "opacity-50" : ""
        }`}
      >
        <form
          className="flex-1 relative"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          <textarea
            id="queryInput"
            name="queryInput"
            ref={textAreaRef}
            defaultValue={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            className={`flex items-center w-full resize-none text-gray-600 rounded border border-accent bg-white p-2 pl-5 pr-16 ${
              isInputDisabled ? "cursor-not-allowed" : ""
            }`}
            style={{
              maxHeight: "120px",
              overflowY: "auto",
              minHeight: "50px",
            }}
            placeholder={
              dragOver ? "Drop files here..." : "Type your message here..."
            }
            disabled={isInputDisabled}
          />
          <div className="absolute right-3 bottom-2 flex gap-2">
            <Upload className="zero-padding-upload  " {...uploadProps}>
              <Tooltip
                title=<span className="text-sm">
                  Upload File{" "}
                  <span className="text-secondary text-xs">(max 5mb)</span>
                </span>
                placement="top"
              >
                <Button type="text" disabled={isInputDisabled} className=" ">
                  <UploadIcon
                    strokeWidth={2}
                    size={26}
                    className="p-1 inline-block w-8 text-accent"
                  />
                </Button>
              </Tooltip>
            </Upload>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={
                isInputDisabled || (text.trim() === "" && fileList.length === 0)
              }
              className={`bg-accent transition duration-300 rounded flex justify-center items-center w-11 h-9 ${
                isInputDisabled || (text.trim() === "" && fileList.length === 0)
                  ? "cursor-not-allowed opacity-50"
                  : "hover:brightness-75"
              }`}
            >
              {loading ? (
                <Cog6ToothIcon className="text-white animate-spin rounded-full h-6 w-6" />
              ) : (
                <PaperAirplaneIcon className="h-6 w-6 text-white" />
              )}
            </button>
          </div>
        </form>
      </div>

      {error && !error.status && (
        <div className="p-2 border rounded mt-4 text-orange-500 text-sm">
          <ExclamationTriangleIcon className="h-5 text-orange-500 inline-block mr-2" />
          {error.message}
        </div>
      )}
    </div>
  );
}
