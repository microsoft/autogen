import * as React from "react";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo } from "../../utils";
import { IStatus } from "../../types";
import { message } from "antd";
import { BounceLoader, Card } from "../../atoms";

const GalleryView = () => {
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const [loading, setLoading] = React.useState(false);
  const [gallery, setGallery] = React.useState<null | any[]>(null);
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

  const galleryRows = gallery?.map((item: any, index: number) => {
    return (
      <div key={"galleryrow" + index}>
        <Card title={item.id}>
          <div>{timeAgo(item.timestamp)}</div>
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
