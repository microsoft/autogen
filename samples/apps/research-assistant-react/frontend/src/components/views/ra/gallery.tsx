import { Button, Empty, List, Modal, Tooltip } from "antd";
import * as React from "react";
import "react-inner-image-zoom/lib/InnerImageZoom/styles.css";
import InnerImageZoom from "react-inner-image-zoom";
import {
  ArrowDownRightIcon,
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ArrowsPointingOutIcon,
} from "@heroicons/react/24/outline";
import { truncateText } from "../../utils";
import { ResizableBox } from "react-resizable";
import { IImageGeneratorConfig } from "../../types";
import { Script } from "gatsby";

const GalleryView = ({
  data,
  config,
}: {
  data: any;
  config: IImageGeneratorConfig;
  setInitImage: (image: any) => void;
}) => {
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [selectedItem, setSelectedItem] = React.useState<number>(0);

  const minImageWidth = 400;

  const downloadBase64File = (base64Data: string, fileName: string) => {
    const linkSource = base64Data;
    const downloadLink = document.createElement("a");
    downloadLink.href = linkSource;
    downloadLink.download = fileName;
    downloadLink.click();
    downloadLink.remove();
  };

  const GalleryCard = ({ item, i }: { item: string; i: number }) => {
    return (
      <div
        className="hover:scale-110 text-primary  drop-shadow-lg hover:drop-shadow-xl hover:z-50 transition duration-300"
        key={"row" + i}
      >
        {/* <img
        className="rounded duration-300 hover:drop-shadow-md  hover:scale-110"
        src={item}
      />{" "} */}

        <InnerImageZoom
          zoomType="hover"
          zoomPreload={true}
          className="w-full rounded rounded-t-none duration-300 hover:z-50"
          src={item}
          hideHint={true}
        />
      </div>
    );
  };

  const selectedImage = data.images?.[selectedItem];

  return (
    <div className=" ">
      <div className=" font-semibold text-primary py-2">
        Results
        <span className="text-xs ml-1 text-accent">{data.length}</span>
      </div>

      {/* <div className="grid grid-cols-4 gap-3">{gallery}</div> */}
      <List
        locale={{ emptyText: <Empty description="No results found" /> }}
        className=""
        grid={{
          gutter: 16,
          xs: 1,
          sm: 2,
          md: 4,
          lg: 4,
          xl: 4,
          xxl: 6,
        }}
        dataSource={data}
        renderItem={(item: any, i: number) => (
          <List.Item>
            <GalleryCard item={item} i={i} />
          </List.Item>
        )}
        pagination={{
          pageSize: 20,
          size: "small",
          hideOnSinglePage: true,
        }}
      />
    </div>
  );
};
export default GalleryView;

{
  /* <ResizableBox
width={200}
height={200}
minConstraints={[500, 500]}
maxConstraints={[500, 500]}
>
<>
  <p>Some contents...</p>
  <p>Some contents...</p>
  <p>Some contents...</p>
  {selectedImage && (
  <div className="border">
    <InnerImageZoom
      zoomType="hover"
      zoomPreload={true}
      className="w-full rounded"
      hideHint={true}
      src={selectedImage}
    />
  </div>
)}
</>
</ResizableBox> */
}
