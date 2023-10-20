import { Button, Pagination } from "antd";
import * as React from "react";
import { CodeBlock } from "../codeblock";

const SkillsView = ({ skills }: any) => {
  const [selectedSkill, setSelectedSkill] = React.useState(0);

  const handlePageChange = (page: number) => {
    setSelectedSkill(page - 1);
  };

  // Reset selectedSkill whenever skills array changes
  React.useEffect(() => {
    setSelectedSkill(0);
  }, [skills]);

  return (
    <div>
      {skills && skills.length > 0 && (
        <>
          {" "}
          <div className="my-2 text-sm">
            {skills.length} skills in this file{" "}
          </div>
          <CodeBlock code={skills[selectedSkill]?.code} language={"python"} />
          <div className="mt-4">
            <Pagination
              onChange={handlePageChange}
              defaultCurrent={1}
              total={skills.length}
              pageSize={1}
              current={selectedSkill + 1}
            />
          </div>
        </>
      )}
    </div>
  );
};

const SkillsFileView = ({ skills }: any) => {
  const [selectedFile, setSelectedFile] = React.useState(0);

  const fileButtons = (skills || []).map((skill: any, i: number) => {
    const file_name = skill?.file_name.split("/").pop();
    const isSelected = selectedFile === i;
    return (
      <Button
        key={"skillbutton" + i}
        onClick={() => setSelectedFile(i)}
        type={`${isSelected ? "primary" : "default"}`}
      >
        {file_name}{" "}
        <span className="text-xs ml-1">({skill?.functions.length})</span>
      </Button>
    );
  });

  return (
    <div>
      <div className="inline-flex gap-3 mb-3">{fileButtons}</div>
      <SkillsView skills={skills[selectedFile]?.functions} />
    </div>
  );
};

export default SkillsFileView;
