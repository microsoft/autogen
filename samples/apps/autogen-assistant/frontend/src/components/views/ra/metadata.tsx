import { DocumentTextIcon, PhotoIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import {
  CodeBlock,
  CollapseBox,
  ExpandView,
  ImageLoader,
  MarkdownView,
} from "../../atoms";
import { formatDuration } from "../../utils";
import { IMetadataFile } from "../../types";

const MetaDataView = ({ metadata }: { metadata: any | null }) => {
  const renderFileContent = (file: IMetadataFile, i: number) => {
    const file_type = file.extension;
    const is_image = ["image"].includes(file.type);
    const is_code = ["code"].includes(file.type);
    const is_pdf = ["pdf"].includes(file.type);
    const file_name = file.name || "unknown";
    const file_content = file.content || "";

    let fileView = null;
    let fileTitle = (
      <div>
        {file.type === "image" ? (
          <PhotoIcon className="h-4 mr-1 inline-block" />
        ) : (
          <DocumentTextIcon className="h-4 mr-1 inline-block" />
        )}{" "}
        <span className="break-all ">{file_name}</span>{" "}
      </div>
    );
    let icon = (
      <div className="p-2 bg-secondary rounded flex items-center justify-center   h-full">
        <div className="">
          <div style={{ fontSize: "2em" }} className="  text-center mb-2">
            {file.extension}
          </div>
          <div>{fileTitle}</div>
        </div>
      </div>
    );
    if (is_image) {
      fileView = (
        <div>
          <div className="mb-2">{fileTitle}</div>
          <ImageLoader
            src={`data:image/${file_type};base64,${file_content}`}
            className="w-full rounded"
          />
        </div>
      );
      icon = fileView;
    } else if (is_code) {
      let decodedContent;
      if (typeof window !== "undefined") {
        // Decode base64 for text-based content only if window is available
        decodedContent = window.atob(file_content);
      } else {
        // On server-side (SSR), just show a placeholder or provide an alternative
        decodedContent = "Loading content...";
      }
      fileView = (
        <div className="h">
          <div className="mb-4">{fileTitle}</div>
          <CodeBlock code={decodedContent} language={"python"} />
        </div>
      );
    } else if (is_pdf) {
      fileView = (
        <div className="h-full">
          <div className="mb-4">{fileTitle}</div>
          <object
            className="w-full rounded"
            data={`data:application/pdf;base64,${file_content}`}
            type="application/pdf"
            width="100%"
            height="400px"
          >
            <p>PDF cannot be displayed.</p>
          </object>
        </div>
      );
    } else {
      fileView = <span>Unsupported file type.</span>;
    }

    return (
      <div className="  h-full rounded">
        <ExpandView className="mb-1" icon={icon}>
          {fileView}
        </ExpandView>
      </div>
    );
  };

  const renderFile = (file: IMetadataFile, i: number) => (
    <div key={"metafilesrow" + i} className="text-primary ">
      {renderFileContent(file, i)}
    </div>
  );

  const files = (metadata.files || []).map(renderFile);

  const messages = (metadata.messages || []).map((message: any, i: number) => (
    <div className="border-b border-dashed" key={"messagerow" + i}>
      <MarkdownView data={message?.content} className="text-sm" />
    </div>
  ));

  const hasContent = files.length > 0;
  const hasMessages = messages.length > 0;

  return (
    <div>
      {hasMessages && (
        <div className="rounded bg-primary p-2">
          <CollapseBox
            open={false}
            title={`Agent Messages (${messages.length} message${
              messages.length > 1 ? "s" : ""
            }) | ${formatDuration(metadata?.time)}`}
          >
            {messages}
          </CollapseBox>
        </div>
      )}
      {hasContent && (
        <div className="rounded bg-primary p-2">
          <CollapseBox
            open={true}
            title={`Results (${files.length} file${
              files.length > 1 ? "s" : ""
            })`}
          >
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {files}
            </div>
          </CollapseBox>
        </div>
      )}
    </div>
  );
};

export default MetaDataView;
