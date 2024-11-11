import React from "react";
import { Select, Button, Popconfirm } from "antd";
import { Edit, Trash2 } from "lucide-react";
import type { TeamListProps } from "./types";
import type { SelectProps } from "antd";

export const TeamList: React.FC<TeamListProps> = ({
  teams,
  currentTeam,
  onSelect,
  onEdit,
  onDelete,
  isLoading,
}) => {
  const options: SelectProps["options"] = [
    {
      label: "Teams",
      options: teams.map((team) => ({
        label: (
          <div className="flex items-center justify-between w-full pr-2">
            <span className="flex-1 truncate">{team.config.name}</span>
            <div className="flex gap-2 ml-2">
              <Button
                type="text"
                size="small"
                className="p-0 min-w-[24px] h-6 text-primary"
                icon={<Edit className="w-4 h-4 text-primary" />}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(team);
                }}
              />
              <Popconfirm
                title="Delete Team"
                description="Are you sure you want to delete this team?"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  if (team.id) onDelete(team.id);
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  type="text"
                  size="small"
                  className="p-0 min-w-[24px] h-6"
                  danger
                  icon={<Trash2 className="w-4 h-4 text-primary" />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </div>
          </div>
        ),
        value: team.id,
      })),
    },
  ];

  return (
    <Select
      className="w-64"
      placeholder={isLoading ? "Loading teams..." : "Select a team"}
      loading={isLoading}
      disabled={isLoading}
      value={currentTeam?.id}
      onChange={(value) => {
        const team = teams.find((t) => t.id === value);
        if (team) onSelect(team);
      }}
      options={options}
      notFoundContent={teams.length === 0 ? "No teams found" : undefined}
      dropdownStyle={{ minWidth: "256px" }}
      listHeight={256}
    />
  );
};
