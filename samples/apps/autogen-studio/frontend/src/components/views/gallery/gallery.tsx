import * as React from "react";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import { IGalleryItem, IStatus } from "../../types";
import { Button, message } from "antd";
import { BounceLoader, Card } from "../../atoms";
import {
  ChevronLeftIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { navigate } from "gatsby";
import ChatBox from "../playground/chatbox";

const GalleryView = ({ location }: any) => {
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const [loading, setLoading] = React.useState(false);
  const [gallery, setGallery] = React.useState<null | IGalleryItem[]>(null);
  const [currentGallery, setCurrentGallery] =
    React.useState<null | IGalleryItem>(null);
  const listGalleryUrl = `${serverUrl}/gallery?user_id=${user?.email}`;
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const [currentGalleryId, setCurrentGalleryId] = React.useState<string | null>(
    null
  );

  React.useEffect(() => {
    // get gallery id from url
    const urlParams = new URLSearchParams(location.search);
    const galleryId = urlParams.get("id");

    if (galleryId) {
      // Fetch gallery details using the galleryId
      fetchGallery(galleryId);
      setCurrentGalleryId(galleryId);
    } else {
      // Redirect to an error page or home page if the id is not found
      // navigate("/");
      fetchGallery(null);
    }
  }, []);

  const fetchGallery = (galleryId: string | null) => {
    const fetchGalleryUrl = galleryId
      ? `${serverUrl}/gallery?gallery_id=${galleryId}`
      : listGalleryUrl;
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
      if (data && data.status) {
        // message.success(data.message);
        console.log("gallery", data);
        if (galleryId) {
          // Set the currently viewed gallery item
          setCurrentGallery(data.data[0]);
        } else {
          setGallery(data.data);
        }
        // Set the list of gallery items
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
    fetchJSON(fetchGalleryUrl, payLoad, onSuccess, onError);
  };

  const GalleryContent = ({ item }: { item: IGalleryItem }) => {
    return (
      <div>
        <div className="mb-4 text-sm">
          This session contains {item.messages.length} messages and was created{" "}
          {timeAgo(item.timestamp)}
        </div>
        <div className="">
          <ChatBox initMessages={item.messages} editable={false} />
        </div>
      </div>
    );
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

  const galleryRows = gallery?.map((item: IGalleryItem, index: number) => {
    const isSelected = currentGallery?.id === item.id;
    return (
      <div key={"galleryrow" + index} className="">
        <Card
          active={isSelected}
          onClick={() => {
            setCurrentGallery(item);
            // add to history
            navigate(`/gallery?id=${item.id}`);
          }}
          className="h-full p-2 cursor-pointer"
          title={truncateText(item.messages[0]?.content || "", 20)}
        >
          <div className="my-2">
            {" "}
            {truncateText(item.messages[0]?.content || "", 80)}
          </div>
          <div className="text-xs">
            {" "}
            {item.messages.length} message{item.messages.length > 1 && "s"}
          </div>
          <div className="my-2 border-t border-dashed w-full pt-2 inline-flex gap-2 ">
            <TagsView tags={item.tags} />{" "}
          </div>
          <div className="text-xs">{timeAgo(item.timestamp)}</div>
        </Card>
      </div>
    );
  });

  return (
    <div className=" ">
      <div className="mb-4 text-2xl">Gallery</div>

      {/* back to gallery button */}

      {currentGallery && (
        <div className="mb-4   w-full">
          <Button
            type="primary"
            onClick={() => {
              setCurrentGallery(null);
              // add to history
              navigate(`/gallery?_=${Date.now()}`);
              if (currentGalleryId) {
                fetchGallery(null);
                setCurrentGalleryId(null);
              }
            }}
            className="bg-primary text-white px-2 py-1 rounded"
          >
            <ChevronLeftIcon className="h-4 w-4 inline mr-1" />
            Back to gallery
          </Button>
        </div>
      )}

      {!currentGallery && (
        <>
          <div>
            View a collection of AutoGen agent specifications and sessions{" "}
          </div>
          <div className="mt-4 grid gap-3 grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {galleryRows}
          </div>
        </>
      )}

      {gallery && gallery.length === 0 && (
        <div className="text-sm border rounded text-secondary p-2">
          <InformationCircleIcon className="h-4 w-4 inline mr-1" />
          No gallery items found. Please create a chat session and publish to
          gallery.
        </div>
      )}

      {currentGallery && (
        <div className="mt-4 border-t pt-2">
          <GalleryContent item={currentGallery} />
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
    </div>
  );
};

export default GalleryView;
