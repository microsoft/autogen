import * as React from "react";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo } from "../../utils";
import { IGalleryItem, IStatus } from "../../types";
import { message } from "antd";
import { BounceLoader, Card } from "../../atoms";
import { InformationCircleIcon } from "@heroicons/react/24/outline";

const GalleryView = () => {
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
    fetchGallery();
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

  const galleryRows = gallery?.map((item: IGalleryItem, index: number) => {
    return (
      <div key={"galleryrow" + index}>
        <Card title={item.id}>
          <div className="my-2"> {item.messages[0].content}</div>
          <div className="my-2">
            <TagsView tags={item.tags} />{" "}
          </div>
          <div className="text-sm">{timeAgo(item.timestamp)}</div>
        </Card>
      </div>
    );
  });

  return (
    <div className=" ">
      <div className="mb-4 text-2xl">Gallery</div>
      <div>View a collection of AutoGen agent specifications and sessions </div>

      <div className="mt-4 grid gap-3 grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {galleryRows}
      </div>

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
    </div>
  );
};

export default GalleryView;
