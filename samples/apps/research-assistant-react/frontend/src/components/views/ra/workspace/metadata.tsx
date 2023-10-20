import { DocumentTextIcon } from "@heroicons/react/24/outline";
import { Tabs } from "antd";
import * as React from "react";
import { CodeBlock } from "../codeblock";
import { has } from "lodash";
import ExpandView from "./expandview";

const MetaDataView = ({
  metadata,
  setMetadata,
}: {
  metadata: any | null;
  setMetadata: any;
}) => {
  let items = [];
  const serverUrl = process.env.GATSBY_API_URL;

  // console.log("****metadata", metadata);

  const scripts = (metadata.scripts || []).map((script: string, i: number) => {
    const script_name = script.split("/").pop();
    return (
      <div key={"scriptrow" + i} className=" text-primary gap-2  ">
        <div className="mb-1">
          <DocumentTextIcon className="h-4 mr-1 inline-block" /> {script_name}
        </div>
        {/* <CodeBlock code={"print('hello world')"} language={"python"} /> */}
      </div>
    );
  });

  const images = (metadata.images || []).map((image: string, i: number) => {
    const image_name = image.split("/").pop();
    const time_nonce = new Date().getTime().toString();
    return (
      <div key={"metaimagesrow" + i} className="text-primary ">
        <ExpandView className="p-2">
          <div className="mb-">
            <DocumentTextIcon className="h-4 mr-1 inline-block" /> {image_name}
          </div>
          <img
            src={`${serverUrl}/${image}?t=${time_nonce}`}
            className="w-full rounded"
          />
        </ExpandView>
      </div>
    );
  });

  const files = (metadata.files || []).map((file: string, i: number) => {
    const file_name = file.split("/").pop();
    return (
      <div key={"metafilesrow" + i} className="text-primary ">
        <DocumentTextIcon className="h-4 mr-1 inline-block" /> {file_name}
      </div>
    );
  });

  if (images.length > 0) {
    items.push({
      label: (
        <div className="text-primary">
          <DocumentTextIcon className="h-4 mr-1 inline-block" /> Images{" "}
          <span className="text-xs">({images.length})</span>
        </div>
      ),
      key: "images",
      children: (
        <div>
          <div className="mb-2">
            {" "}
            The following images were created in creating your response.
          </div>
          {images}
        </div>
      ),
    });
  }

  // if (scripts.length > 0) {
  //   items.push({
  //     label: (
  //       <div className="text-primary">
  //         <DocumentTextIcon className="h-4 mr-1 inline-block" /> Scripts{" "}
  //         <span className="text-xs">({scripts.length})</span>
  //       </div>
  //     ),
  //     key: "scripts",
  //     children: (
  //       <div>
  //         <div className="mb-2">
  //           {" "}
  //           The following scripts were created in creating your response.
  //         </div>
  //         {scripts}
  //       </div>
  //     ),
  //   });
  // }

  // if (metadata["code"] && metadata["code"].length > 0) {
  //   items.push({
  //     label: (
  //       <div className="text-primary">
  //         <DocumentTextIcon className="h-4 mr-1 inline-block" /> Code{" "}
  //       </div>
  //     ),
  //     key: "code",
  //     children: (
  //       <div className="text-primary ">
  //         <div className="mb-2">
  //           {" "}
  //           The following code was used in creating your response.
  //         </div>
  //         <CodeBlock
  //           wrapLines={true}
  //           code={metadata["code"]}
  //           language={metadata["language"]}
  //         />
  //       </div>
  //     ),
  //   });
  // }

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
