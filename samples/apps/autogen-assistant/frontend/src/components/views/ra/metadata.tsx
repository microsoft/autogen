import { DocumentTextIcon, PhotoIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import {
  CodeBlock,
  CodeLoader,
  CollapseBox,
  ExpandView,
  ImageLoader,
  MarkdownView,
  PdfViewer,
} from "../../atoms";
import { formatDuration, getServerUrl } from "../../utils";
import { IMetadataFile } from "../../types";
import Icon from "../../icons";

const MetaDataView = ({ metadata }: { metadata: any | null }) => {
  console.log(metadata);
  const serverUrl = getServerUrl();
  const renderFileContent = (file: IMetadataFile, i: number) => {
    const file_type = file.extension;
    const is_image = ["image"].includes(file.type);
    const is_code = ["code"].includes(file.type);
    const is_pdf = ["pdf"].includes(file.type);
    const file_name = file.name || "unknown";
    const file_path = file.path || "unknown";

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
            src={`${serverUrl}/${file_path}`}
            className="w-full rounded"
          />
        </div>
      );
      icon = fileView;
    } else if (is_code) {
      fileView = (
        <div className="h">
          <div className="mb-4">{fileTitle}</div>
          <CodeLoader
            url={`${serverUrl}/${file_path}`}
            className="w-full rounded"
          />
        </div>
      );
      icon = (
        <div className="   relative rounded   h-full">
          <div className="absolute rounded p-2 bg-secondary top-0 ">
            {fileTitle}
          </div>
          <div
            style={{ minHeight: "150px" }}
            className="bg-secondary  h-full w-full rounded  flex items-center justify-center text-primary"
          >
            <Icon icon="python" size={14} />
          </div>
        </div>
      );
    } else if (is_pdf) {
      fileView = (
        <div className="h-full">
          <div className="mb-4">{fileTitle}</div>
          <PdfViewer url={`${serverUrl}/${file_path}`} />
        </div>
      );

      icon = (
        <div className="   relative rounded   h-full">
          <div className="absolute rounded p-2 bg-secondary top-0 ">
            {fileTitle}
          </div>
          <div
            style={{ minHeight: "150px" }}
            className="bg-secondary h-full w-full rounded  flex items-center justify-center text-primary "
          >
            <Icon icon="pdf" size={14} />
          </div>
        </div>
      );
    } else {
      fileView = <span>Unsupported file type.</span>;
    }

    return (
      <div className="  h-full rounded">
        <ExpandView className="mb-1" icon={icon} title={file_name}>
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
