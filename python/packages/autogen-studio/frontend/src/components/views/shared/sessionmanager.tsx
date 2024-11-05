// SessionManager.tsx
import React, { useEffect, useState, useContext, useCallback } from "react";
import {
  Select,
  Button,
  Input,
  message,
  Popconfirm,
  Collapse,
  Badge,
  CollapseProps,
} from "antd";
import { Plus, Edit, Trash2, ChevronDown } from "lucide-react";
import { getServerUrl } from "../../utils";
import { useConfigStore } from "../../../hooks/store";
import { appContext } from "../../../hooks/provider";
// import type { Session, SessionUrls, User } from "./types";

export interface SessionUrls {
  listSessionUrl: string;
  createSessionUrl: string;
  getSessionUrl: (id: number) => string;
  updateSessionUrl: (id: number) => string;
  deleteSessionUrl: (id: number) => string;
}

const { Panel } = Collapse;

const SessionManager: React.FC = () => {
  // States for managing UI operations
  const [fetchingList, setFetchingList] = useState(false);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");
  const [editingSession, setEditingSession] = useState<number | null>(null);
  const [editedName, setEditedName] = useState("");
  const [isOpen, setIsOpen] = useState(true);

  // URLs state
  const [urls, setUrls] = useState<SessionUrls | null>(null);

  // Global context and store
  const { user } = useContext(appContext);
  const { session, setSession, sessions, setSessions } = useConfigStore();

  // Initialize URLs when user changes
  useEffect(() => {
    if (user?.email) {
      const serverUrl = getServerUrl();
      setUrls({
        listSessionUrl: `${serverUrl}/sessions?user_id=${user.email}`,
        createSessionUrl: `${serverUrl}/sessions`,
        getSessionUrl: (id: number) =>
          `${serverUrl}/sessions/${id}?user_id=${user.email}`,
        updateSessionUrl: (id: number) =>
          `${serverUrl}/sessions/${id}?user_id=${user.email}`,
        deleteSessionUrl: (id: number) =>
          `${serverUrl}/sessions/${id}?user_id=${user.email}`,
      });
    }
  }, [user]);

  // Fetch all sessions
  const fetchSessions = useCallback(async () => {
    if (!urls) return;

    try {
      setFetchingList(true);
      const response = await fetch(urls.listSessionUrl);
      const data = await response.json();

      if (data.status) {
        setSessions(data.data);
      } else {
        message.error("Failed to load sessions");
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
      message.error("Error loading sessions");
    } finally {
      setFetchingList(false);
    }
  }, [urls, setSessions]);

  // Create new session
  const createSession = useCallback(async () => {
    if (!urls || !user?.email) return;

    if (!newSessionName.trim()) {
      message.warning("Please enter a session name");
      return;
    }

    try {
      setCreating(true);
      const response = await fetch(urls.createSessionUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newSessionName.trim(),
          user_id: user.email,
        }),
      });

      const data = await response.json();
      if (data.status) {
        message.success("Session created");
        setSession(data.data);
        setSessions([...sessions, data.data]);
        resetCreateForm();
      } else {
        message.error("Failed to create session");
      }
    } catch (error) {
      console.error("Error creating session:", error);
      message.error("Error creating session");
    } finally {
      setCreating(false);
    }
  }, [urls, user?.email, newSessionName, sessions, setSession, setSessions]);

  // Update existing session
  const updateSession = useCallback(async () => {
    if (!urls || !user?.email || !editingSession) return;

    if (!editedName.trim()) {
      message.warning("Please enter a session name");
      return;
    }

    try {
      setUpdating(true);
      const response = await fetch(urls.updateSessionUrl(editingSession), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: editingSession,
          name: editedName.trim(),
          user_id: user.email,
        }),
      });

      const data = await response.json();
      if (data.status) {
        message.success("Session updated");
        setSessions(
          sessions.map((s) =>
            s.id === editingSession ? { ...s, name: editedName.trim() } : s
          )
        );
        if (session?.id === editingSession) {
          setSession({ ...session, name: editedName.trim() });
        }
        resetEditForm();
      } else {
        message.error("Failed to update session");
      }
    } catch (error) {
      console.error("Error updating session:", error);
      message.error("Error updating session");
    } finally {
      setUpdating(false);
    }
  }, [
    urls,
    user?.email,
    editingSession,
    editedName,
    sessions,
    session,
    setSession,
    setSessions,
  ]);

  // Delete session
  const deleteSession = useCallback(
    async (sessionId: number) => {
      if (!urls) return;

      try {
        const response = await fetch(urls.deleteSessionUrl(sessionId), {
          method: "DELETE",
        });

        const data = await response.json();
        if (data.status) {
          message.success("Session deleted");
          setSessions(sessions.filter((s) => s.id !== sessionId));
          if (session?.id === sessionId) {
            setSession(null);
          }
        } else {
          message.error("Failed to delete session");
        }
      } catch (error) {
        console.error("Error deleting session:", error);
        message.error("Error deleting session");
      }
    },
    [urls, sessions, session, setSession, setSessions]
  );

  // Load specific session
  const handleSessionSelect = useCallback(
    async (sessionId: number) => {
      if (!urls) return;

      try {
        setFetchingList(true);
        const response = await fetch(urls.getSessionUrl(sessionId));
        const data = await response.json();

        if (data.status) {
          setSession(data.data);
        } else {
          message.error("Failed to load session");
        }
      } catch (error) {
        console.error("Error loading session:", error);
        message.error("Error loading session");
      } finally {
        setFetchingList(false);
      }
    },
    [urls, setSession]
  );

  // Form reset handlers
  const resetCreateForm = () => {
    setNewSessionName("");
    setShowCreateForm(false);
    setCreating(false);
  };

  const resetEditForm = () => {
    setEditingSession(null);
    setEditedName("");
    setUpdating(false);
  };

  const startEditing = (sessionId: number) => {
    const sessionToEdit = sessions.find((s) => s.id === sessionId);
    if (sessionToEdit) {
      setEditingSession(sessionId);
      setEditedName(sessionToEdit.name);
      setShowCreateForm(false);
    }
  };

  // Load sessions on mount
  useEffect(() => {
    if (urls) {
      fetchSessions();
    }
  }, [urls, fetchSessions]);

  // Custom header with session count
  const CollapsibleHeader = () => (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-3">
        <span className="font-medium">Sessions</span>
        <Badge
          count={sessions.length}
          showZero
          className="site-badge-count-4"
          style={{ backgroundColor: "#52525b" }}
        />
      </div>
      {session && (
        <span className="text-sm text-gray-500">Current: {session.name}</span>
      )}
    </div>
  );

  const handleNewNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setNewSessionName(e.target.value);
    },
    []
  );

  const handleEditNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setEditedName(e.target.value);
    },
    []
  );

  // Session management content
  const SessionContent = () => (
    <div className="flex gap-2 items-center">
      {showCreateForm ? (
        <div className="flex gap-2 items-center w-full">
          <Input
            key="create-session-input"
            placeholder="Enter session name"
            value={newSessionName}
            onChange={handleNewNameChange}
            onPressEnter={createSession}
            className="flex-1"
            maxLength={100}
            disabled={creating}
            autoFocus
          />
          <Button onClick={createSession} loading={creating} type="primary">
            Create
          </Button>
          <Button onClick={resetCreateForm} disabled={creating}>
            Cancel
          </Button>
        </div>
      ) : editingSession ? (
        <div className="flex gap-2 items-center w-full">
          <Input
            key="edit-session-input"
            placeholder="Enter new session name"
            value={editedName}
            onChange={handleEditNameChange}
            onPressEnter={updateSession}
            className="flex-1"
            maxLength={100}
            disabled={updating}
            autoFocus
          />
          <Button onClick={updateSession} loading={updating} type="primary">
            Update
          </Button>
          <Button onClick={resetEditForm} disabled={updating}>
            Cancel
          </Button>
        </div>
      ) : (
        <>
          <Select
            className="w-64"
            placeholder={
              fetchingList ? "Loading sessions..." : "Select a session"
            }
            loading={fetchingList}
            disabled={fetchingList}
            onChange={handleSessionSelect}
            value={session?.id}
            options={sessions.map((s) => ({
              label: (
                <div className="flex items-center justify-between">
                  <span>{s.name}</span>
                  <div className="flex gap-2">
                    <Button
                      type="text"
                      size="small"
                      className="p-0"
                      icon={<Edit className="w-4 h-4" />}
                      onClick={(e) => {
                        e.stopPropagation();
                        startEditing(s.id);
                      }}
                    />
                    <Popconfirm
                      title="Delete Session"
                      description="Are you sure you want to delete this session?"
                      onConfirm={(e) => {
                        e?.stopPropagation();
                        deleteSession(s.id);
                      }}
                      onCancel={(e) => e?.stopPropagation()}
                    >
                      <Button
                        type="text"
                        size="small"
                        className="p-0"
                        danger
                        icon={<Trash2 className="w-4 h-4" />}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Popconfirm>
                  </div>
                </div>
              ),
              value: s.id,
            }))}
            notFoundContent={
              sessions.length === 0 ? "No sessions found" : undefined
            }
          />
          <Button
            onClick={() => setShowCreateForm(true)}
            icon={<Plus className="w-4 h-4" />}
          >
            New Session
          </Button>
        </>
      )}
    </div>
  );

  const items: CollapseProps["items"] = [
    {
      key: "1",
      label: <CollapsibleHeader />,
      children: <SessionContent />,
    },
  ];

  return (
    <Collapse
      items={items}
      className="bg-secondary border-0 shadow-sm"
      defaultActiveKey={["1"]}
      expandIcon={({ isActive }) => (
        <ChevronDown
          className={`w-4 h-4 transition-transform duration-200 ${
            isActive ? "rotate-180" : ""
          }`}
        />
      )}
      onChange={(keys) => setIsOpen(keys.includes("1"))}
    />
  );
};

export default SessionManager;
