import * as React from "react";
import { IStatus } from "../../../types";

const RenderFileView = ({ url }: any) => {
  const fetchFile = (
    url: string | URL,
    onSuccess: (data: { fileType: string; content: any }) => void,
    onError: (error: IStatus) => void
  ) => {
    return fetch(url)
      .then(function (response) {
        if (response.status !== 200) {
          console.log(
            "Looks like there was a problem. Status Code: " + response.status,
            response
          );
          onError({
            status: false,
            message:
              "Connection error " + response.status + " " + response.statusText,
          });
          return;
        }

        const fileType = url.split(".").pop()?.toLowerCase() || "unknown";

        if (fileType === "pdf") {
          onSuccess({ fileType, content: url }); // return the same URL for embedding
        } else {
          return response.text().then(function (content) {
            onSuccess({ fileType, content });
          });
        }
      })
      .catch(function (err) {
        console.log("Fetch Error :-S", err);
        onError({
          status: false,
          message: `There was an error connecting to server. (${err}) `,
        });
      });
  };
  return (
    <div className="mt-4 text-primary py-3  mb-6  border-secondary "></div>
  );
};
export default RenderFileView;
