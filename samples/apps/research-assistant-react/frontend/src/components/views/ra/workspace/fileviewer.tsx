import {
  ChevronLeftIcon,
  ChevronRightIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import * as React from "react";
import { fetchJSON } from "../../../utils";
import { appContext } from "../../../../hooks/provider";

const FileViewer = ({ setMessages, notify, skillup }: any) => {
  const initFiles = [
    "domain.png",
    "chart_stuff.py",
    "sea_leve.txt",
    "data.csv",
  ];

  const { user } = React.useContext(appContext);

  const [error, setError] = React.useState<any | null>(null);
  const [loading, setLoading] = React.useState<boolean>(false);

  const [files, setFiles] = React.useState<string[]>(initFiles);
  const serverUrl = process.env.GATSBY_API_URL;
  const listFilesUrl = `${serverUrl}/userfiles?user_id=${user?.email}`;

  const sanitizeFilePaths = (files: any) => {
    const sanitizedFiles = files.map((file: string) => {
      // only return file names
      return { name: file.split("/").pop(), path: file };
    });
    return sanitizedFiles;
  };

  const listFiles = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
    };
    const onSuccess = (data: any) => {
      // console.log("success", data);
      if (data && data.status) {
        setFiles(sanitizeFilePaths(data.files));
      } else {
        setError(data);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      setLoading(false);
    };
    fetchJSON(listFilesUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      listFiles();
    }
  }, []);

  const filesView = files.map((file: string, i: number) => {
    return (
      <div key={"filerow" + i} className="border-b text-md mt-2 pb-2">
        <div className="flex text-sm">
          <div className="flex-1">{file.name}</div>
          <div
            role="button"
            onClick={() => {
              console.log("deleting file", file);
            }}
            className="hover:text-accent duration-300"
          >
            <TrashIcon className="w-4 h-4 inline-block" />{" "}
          </div>
        </div>
      </div>
    );
  });

  return (
    <div>
      <div className="border-b text-md mt-2 pb-2"> User Files</div>
      <div>{filesView}</div>
    </div>
  );
};

export default FileViewer;
