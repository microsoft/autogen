import { DocumentTextIcon } from "@heroicons/react/24/outline";
import * as React from "react";
import { CollapseBox, ExpandView, MarkdownView } from "../../atoms";
import { formatDuration, getServerUrl } from "../../utils";

const MetaDataView = ({ metadata }: { metadata: any | null }) => {
  const serverUrl = getServerUrl();

  const renderFile = (file: string, i: number) => {
    const file_type = file.split(".").pop() || "";
    const image_types = ["png", "jpg", "jpeg", "gif", "svg"];
    const is_image = image_types.includes(file_type);
    const time_nonce = new Date().getTime().toString();
    const file_name = file.split("/").pop() || "";

    if (is_image) {
      return (
        <div key={"metafilesrow" + i} className="text-primary ">
          <ExpandView className="lg:w-3/4  xl:w-1/2 2xl:w-1/4 mb-1">
            <div className="mb-2">
              <DocumentTextIcon className="h-4 mr-1 inline-block" /> {file_name}
            </div>
            <img
              src={`${serverUrl}/${file}?t=${time_nonce}`}
              className="w-full  rounded"
            />
          </ExpandView>
        </div>
      );
    } else {
      return (
        <div key={"metafilesrow" + i} className="text-primary text-xs">
          <DocumentTextIcon className="h-4 mr-1 inline-block" /> {file_name}
        </div>
      );
    }
  };

  const files = (metadata.files || []).map((file: string, i: number) => {
    return (
      <div
        key={"metafilesrow" + i}
        className="text-primary border-b border-dashed py-2"
      >
        {renderFile(file, i)}
      </div>
    );
  });

  const messages = (metadata.messages || []).map((message: any, i: number) => {
    return (
      <div className="border-b  border-dashed" key={"messagerow" + i}>
        <MarkdownView data={message?.content} className="text-sm" />
      </div>
    );
  });

  const hasContent = files.length > 0;
  const hasMessages = messages.length > 0;
  return (
    <div>
      {hasMessages && (
        <div className="  rounded bg-primary  p-2 ">
          <CollapseBox
            open={false}
            title={`Agent Messages (${messages.length} message${
              messages.length > 1 ? "s" : ""
            }) | ${formatDuration(metadata?.time)}`}
          >
            <div
              // style={{ maxHeight: "300px" }}
              className=" "
            >
              {messages}
            </div>
          </CollapseBox>
        </div>
      )}
      {hasContent && (
        <div className="  rounded bg-primary  p-2 ">
          <CollapseBox
            open={true}
            title={`Results (${files.length} file${
              files.length > 1 ? "s" : ""
            })`}
          >
            <div className="mt-2 ">{files}</div>
          </CollapseBox>
        </div>
      )}
    </div>
  );
};
export default MetaDataView;
