import { DocumentTextIcon } from "@heroicons/react/24/outline";
import { Tabs } from "antd";
import * as React from "react";
import { ExpandView } from "../../atoms";

const MetaDataView = ({
  metadata,
  setMetadata,
}: {
  metadata: any | null;
  setMetadata: any;
}) => {
  let items = [];
  const serverUrl = process.env.GATSBY_API_URL;

  const renderFile = (file: string, i: number) => {
    const file_type = file.split(".").pop() || "";
    const image_types = ["png", "jpg", "jpeg", "gif", "svg"];
    const is_image = image_types.includes(file_type);
    const time_nonce = new Date().getTime().toString();
    const file_name = file.split("/").pop() || "";

    if (is_image) {
      return (
        <div key={"metafilesrow" + i} className="text-primary ">
          <ExpandView className="p-2 mb-1">
            <div className="mb-">
              <DocumentTextIcon className="h-4 mr-1 inline-block" /> {file_name}
            </div>
            <img
              src={`${serverUrl}/${file}?t=${time_nonce}`}
              className="w-full rounded"
            />
          </ExpandView>
        </div>
      );
    } else {
      return (
        <div key={"metafilesrow" + i} className="text-primary ">
          <DocumentTextIcon className="h-4 mr-1 inline-block" /> {file_name}
        </div>
      );
    }
  };

  const files = (metadata.files || []).map((file: string, i: number) => {
    return (
      <div key={"metafilesrow" + i} className="text-primary ">
        {renderFile(file, i)}
      </div>
    );
  });

  if (files.length > 0) {
    items.push({
      label: (
        <div className="text-primary">
          <DocumentTextIcon className="h-4 mr-1 inline-block" /> Files{" "}
          <span className="text-xs">({files.length})</span>
        </div>
      ),
      key: "files",
      children: (
        <div>
          <div className="mb-2">
            {" "}
            The following files were created in creating your response.
          </div>
          {files}
        </div>
      ),
    });
  }

  const hasContent = items.length > 0;
  return (
    <div className=" -mt-3 p-2 ">
      {hasContent && <Tabs defaultActiveKey="chat" items={items} />}
    </div>
  );
};
export default MetaDataView;
