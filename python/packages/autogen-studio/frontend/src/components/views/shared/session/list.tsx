import React from "react";
import { Select, Button, Popconfirm } from "antd";
import { Edit, Trash2 } from "lucide-react";
import type { SessionListProps } from "./types";
import type { SelectProps } from "antd";

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  currentSession,
  onSelect,
  onEdit,
  onDelete,
  isLoading,
}) => {
  const options: SelectProps["options"] = [
    {
      label: "Sessions",
      options: sessions.map((session) => ({
        label: (
          <div className="flex items-center justify-between w-full pr-2">
            <span className="flex-1 truncate">{session.name}</span>
            <div className="flex gap-2 ml-2">
              <Button
                type="text"
                size="small"
                className="p-0 min-w-[24px] h-6 text-primary"
                icon={<Edit className="w-4 h-4 text-primary" />}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(session);
                }}
              />
              <Popconfirm
                title="Delete Session"
                description="Are you sure you want to delete this session?"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  if (session.id) onDelete(session.id);
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
        value: session.id,
      })),
    },
  ];

  return (
    <Select
      className="w-64"
      placeholder={isLoading ? "Loading sessions..." : "Select a session"}
      loading={isLoading}
      disabled={isLoading}
      value={currentSession?.id}
      onChange={(value) => {
        const session = sessions.find((s) => s.id === value);
        if (session) onSelect(session);
      }}
      options={options}
      notFoundContent={sessions.length === 0 ? "No sessions found" : undefined}
      dropdownStyle={{ minWidth: "256px" }}
      listHeight={256}
    />
  );
};
