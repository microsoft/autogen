import * as React from "react";

const TestView = () => {
  React.useEffect(() => {
    console.log("test view");
  });
  return <div className="h-full">test</div>;
};
export default TestView;
