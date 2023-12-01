import * as React from "react";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import { IGalleryItem, IStatus } from "../../types";
import { message } from "antd";
import { BounceLoader, Card } from "../../atoms";
import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { Link, PageProps } from "gatsby";

const GalleryDetailView = ({ location }: PageProps) => {
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const [loading, setLoading] = React.useState(false);
  const [gallery, setGallery] = React.useState<null | IGalleryItem[]>(null);
  const listGalleryUrl = `${serverUrl}/gallery?user_id=${user?.email}`;
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  React.useEffect(() => {
    // get gallery id from url
    const urlParams = new URLSearchParams(location.search);
    const galleryId = urlParams.get("id");

    if (galleryId) {
      // Fetch gallery details using the galleryId
      // fetchGallery(galleryId);
    } else {
      // Redirect to an error page or home page if the id is not found
      // navigate("/");
      setError({
        status: false,
        message: "A Gallery ID is required to view the gallery. ",
      });
    }
  }, []);

  const fetchGallery = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        console.log("gallery", data);
        setGallery(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(listGalleryUrl, payLoad, onSuccess, onError);
  };

  const TagsView = ({ tags }: { tags: string[] }) => {
    const tagsView = tags.map((tag: string, index: number) => {
      return (
        <div key={"tag" + index} className="mr-2 inline-block">
          <span className="text-xs bg-secondary border px-3 p-1 rounded">
            {tag}
          </span>
        </div>
      );
    });
    return <div className="flex flex-wrap">{tagsView}</div>;
  };

  // const galleryRows = gallery?.map((item: IGalleryItem, index: number) => {
  //   return (
  //     <div key={"galleryrow" + index} className="">
  //       <Card
  //         className="h-full p-2 cursor-pointer"
  //         title={truncateText(item.messages[0].content, 20)}
  //       >
  //         <div className="my-2">
  //           {" "}
  //           {truncateText(item.messages[0].content, 80)}
  //         </div>
  //         <div className="my-2 border-t border-dashed w-full pt-2 inline-flex gap-2 ">
  //           <TagsView tags={item.tags} />{" "}
  //         </div>
  //         <div className="text-xs">{timeAgo(item.timestamp)}</div>
  //       </Card>
  //     </div>
  //   );
  // });

  return (
    <div className=" ">
      <div className="mb-4 text-2xl">Item Details</div>
      <div>V </div>

      {gallery && gallery.length === 0 && (
        <div className="text-sm border rounded text-secondary p-2">
          <InformationCircleIcon className="h-4 w-4 inline mr-1" />
          No gallery items found. Please create a chat session and publish to
          gallery.
        </div>
      )}

      {loading && (
        <div className="w-full text-center boder mt-4">
          <div>
            {" "}
            <BounceLoader />
          </div>
          loading gallery
        </div>
      )}

      {error && !error.status && (
        <div className="p-2 border rounded mt-4 text-sm">
          {" "}
          <ExclamationTriangleIcon className="h-5  inline-block mr-2" />{" "}
          <span className=" text-orange-500 inline-block ">
            {" "}
            {error.message}
          </span>{" "}
          Go back to{" "}
          <span className="underline">
            <Link to="/gallery">Gallery</Link>
          </span>
        </div>
      )}
    </div>
  );
};

export default GalleryDetailView;
