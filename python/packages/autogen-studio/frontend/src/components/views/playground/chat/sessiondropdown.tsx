import * as React from "react";
import { Dropdown, Input, MenuProps } from "antd";
import { ChevronDown, TextSearch } from "lucide-react";
import { Session } from "../../../types/datamodel";
import { getRelativeTimeString } from "../../atoms";

interface SessionDropdownProps {
  session: Session | null;
  availableSessions: Session[];
  onSessionChange: (session: Session) => void;
}

const SessionDropdown: React.FC<SessionDropdownProps> = ({
  session,
  availableSessions,
  onSessionChange,
}) => {
  const [search, setSearch] = React.useState<string>("");

  // Filter sessions based on search input
  const filteredSessions = availableSessions.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase())
  );

  // This needs to follow the exact MenuProps structure from antd
  const items: MenuProps["items"] = [
    {
      type: "group",
      key: "search-sessions",
      label: (
        <div>
          <div className="text-xs text-secondary mb-1">Search sessions</div>
          <Input
            prefix={<TextSearch className="w-4 h-4" />}
            placeholder="Search sessions"
            onChange={(e) => setSearch(e.target.value)}
            onClick={(e) => e.stopPropagation()} // Prevent dropdown from closing
          />
        </div>
      ),
    },
    {
      type: "divider",
    },
    ...filteredSessions.map((s) => ({
      key: (s.id || "").toString(),
      label: (
        <div className="py-1">
          <div className="font-medium">{s.name}</div>
          <div className="text-xs text-secondary">
            {getRelativeTimeString(s.updated_at || "")}
          </div>
        </div>
      ),
    })),
  ];

  const handleMenuClick: MenuProps["onClick"] = ({ key }) => {
    const selectedSession = availableSessions.find((s) => s.id === Number(key));
    if (selectedSession) {
      onSessionChange(selectedSession);
    }
  };

  return (
    <Dropdown menu={{ items, onClick: handleMenuClick }} trigger={["click"]}>
      <div className="cursor-pointer flex items-center gap-2">
        <span className="text-primary font-medium">
          {session?.name || "Select Session"}
        </span>
        <ChevronDown className="w-4 h-4 text-secondary" />
      </div>
    </Dropdown>
  );
};

export default SessionDropdown;
