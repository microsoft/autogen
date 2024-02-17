import {
  DocumentTextIcon,
  PhotoIcon,
  VideoCameraIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import {
  CodeBlock,
  CodeLoader,
  CsvLoader,
  CollapseBox,
  ExpandView,
  GroupView,
  ImageLoader,
  MarkdownView,
  PdfViewer,
  AgentRow,
} from "../../atoms";
import { formatDuration, getServerUrl } from "../../utils";
import { IMetadataFile } from "../../types";
import Icon from "../../icons";

const MetaDataView = ({ metadata }: { metadata: any | null }) => {
  const serverUrl = getServerUrl();
  const renderFileContent = (file: IMetadataFile, i: number) => {
    const file_type = file.extension;
    const is_image = ["image"].includes(file.type);
    const is_code = ["code"].includes(file.type);
    const is_csv = ["csv"].includes(file.type);
    const is_pdf = ["pdf"].includes(file.type);
    const is_video = ["video"].includes(file.type);
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
    } else if (is_video) {
      fileView = (
        <div className="mb-2">
          <a href={`${serverUrl}/${file_path}`}>{fileTitle}</a>
          <video controls className="w-full rounded">
            <source
              src={`${serverUrl}/${file_path}`}
              type={`video/${file_type}`}
            />
            Your browser does not support the video tag.
          </video>
        </div>
      );

      // Update icon to show a video-related icon
      icon = (
        <div className="   relative rounded   h-full">
          <div className="absolute rounded p-2 bg-secondary top-0 ">
            {fileTitle}
          </div>
          <div
            style={{ minHeight: "150px" }}
            className="bg-secondary h-full w-full rounded  flex items-center justify-center text-primary "
          >
            <VideoCameraIcon className="h-14 w-14" />
          </div>
        </div>
      );
    } else if (is_csv) {
      fileView = (
        <div className="h">
          <a href={`${serverUrl}/${file_path}`}>
            <div className="mb-4">{fileTitle}</div>
          </a>
          <CsvLoader
            csvUrl={`${serverUrl}/${file_path}`}
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
            <Icon icon="csv" size={14} />
          </div>
        </div>
      );
    } else if (is_code) {
      fileView = (
        <div className="h">
          <a
            href={`${serverUrl}/${file_path}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="mb-4">{fileTitle}</div>
          </a>
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
          <div className="mb-4">
            <a
              href={`${serverUrl}/${file_path}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {fileTitle}
            </a>
          </div>
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

  const messages = (metadata.messages || []).map((message: any, i: number) => {
    return (
      <div className=" mb-2 border-dashed" key={"messagerow" + i}>
        <AgentRow message={message} />
      </div>
    );
  });

  const hasContent = files.length > 0;
  const hasMessages = messages.length > 0;

  return (
    <div>
      {hasMessages && (
        <div className="rounded   bg-primary  ">
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
        <div className="rounded mt-2">
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
