import * as React from "react";
import { Empty, List } from "antd";
import { loadJSONData, truncateText } from "../utils";
import { Card, SectionHeader } from "../atoms";
import { DatabaseIcon } from "@heroicons/react/outline";

const DatasetView = () => {
  const serverUrl = process.env.GATSBY_API_URL;
  const [datasets, setDatasets] = React.useState([]);
  React.useEffect(() => {
    loadJSONData(serverUrl + "/datasets")
      .then((data) => {
        if (data) {
          setDatasets(data);
        }
      })
      .catch((err) => {
        console.log("err", err);
      });
  }, []);

  const getResultCard = function (data: any, i: number) {
    return (
      <div key={"row" + i}>
        {data.date}
        <Card title={data} subtitle={data} />
      </div>
    );
  };
  return (
    <div className="">
      <SectionHeader
        icon={
          <DatabaseIcon className="inline-block h-7 text-green-600 -mt-1 mr-1" />
        }
        count={datasets?.length || 0}
        title={datasets.length === 1 ? "Dataset" : "Datasets"}
      ></SectionHeader>
      <div className=" ">
        <List
          locale={{ emptyText: <Empty description="No datasets found" /> }}
          className=""
          grid={{
            gutter: 16,
            xs: 1,
            sm: 2,
            md: 4,
            lg: 4,
            xl: 6,
            xxl: 8,
          }}
          dataSource={datasets}
          renderItem={(item, i) => (
            <List.Item className=" h-full">{getResultCard(item, i)}</List.Item>
          )}
          pagination={{
            pageSize: 20,
            size: "small",
            hideOnSinglePage: true,
          }}
        />
      </div>
    </div>
  );
};
export default DatasetView;
