import React, { useCallback, useEffect, useState, useContext } from "react";
import { Button, message, Collapse, Badge, CollapseProps } from "antd";
import { Plus, ChevronDown } from "lucide-react";
import { useConfigStore } from "../../../../hooks/store";
import { appContext } from "../../../../hooks/provider";
import { sessionAPI } from "./api";
import { SessionList } from "./list";
import { SessionEditor } from "./editor";
import type { Session } from "../../../types/datamodel";

export const SessionManager: React.FC = () => {
  // UI State
  const [isLoading, setIsLoading] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<Session | undefined>();

  // Global context and store
  const { user } = useContext(appContext);
  const { session, setSession, sessions, setSessions } = useConfigStore();

  // Fetch all sessions
  const fetchSessions = useCallback(async () => {
    if (!user?.email) return;

    try {
      setIsLoading(true);
      const data = await sessionAPI.listSessions(user.email);
      setSessions(data);
      if (!session && data.length > 0) {
        setSession(data[0]);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
      message.error("Error loading sessions");
    } finally {
      setIsLoading(false);
    }
  }, [user?.email, setSessions]);

  // Handle session operations
  const handleSaveSession = async (sessionData: Partial<Session>) => {
    if (!user?.email) return;

    try {
      if (sessionData.id) {
        const updated = await sessionAPI.updateSession(
          sessionData.id,
          sessionData,
          user.email
        );
        setSessions(
          sessions.map((s) => (s.id && s.id === updated.id ? updated : s))
        );
        if (session?.id === updated.id) {
          setSession(updated);
        }
      } else {
        const created = await sessionAPI.createSession(sessionData, user.email);
        setSession(created);
        setSessions([...sessions, created]);
      }
      setIsEditorOpen(false);
      setEditingSession(undefined);
    } catch (error) {
      throw error;
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    if (!user?.email) return;

    try {
      await sessionAPI.deleteSession(sessionId, user.email);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (sessions.length > 0) {
        setSession(sessions[0]);
      }
      if (session?.id === sessionId) {
        setSession(null);
      }
      message.success("Session deleted");
    } catch (error) {
      console.error("Error deleting session:", error);
      message.error("Error deleting session");
    }
  };

  const handleSelectSession = async (selectedSession: Session) => {
    if (!user?.email || !selectedSession.id) return;

    try {
      setIsLoading(true);
      const data = await sessionAPI.getSession(selectedSession.id, user.email);
      setSession(data);
    } catch (error) {
      console.error("Error loading session:", error);
      message.error("Error loading session");
    } finally {
      setIsLoading(false);
    }
  };

  // Load sessions on mount
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

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

  // Session management content
  const SessionContent = () => (
    <div className="flex gap-2 items-center">
      {sessions && sessions.length > 0 && (
        <SessionList
          sessions={sessions}
          currentSession={session}
          onSelect={handleSelectSession}
          onEdit={(session) => {
            setEditingSession(session);
            setIsEditorOpen(true);
          }}
          onDelete={handleDeleteSession}
          isLoading={isLoading}
        />
      )}
      <div className="relative">
        <Button
          type="primary"
          onClick={() => {
            setEditingSession(undefined);
            setIsEditorOpen(true);
          }}
          icon={<Plus className="w-4 h-4" />}
        >
          New Session{" "}
          {sessions.length === 0 && (
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-secondary"></span>
            </span>
          )}
        </Button>
      </div>
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
    <>
      <div className="bg-secondary rounded p-2">
        <div className="text-xs pb-2">
          Sessions <span className="px-1 text-accent">{sessions.length} </span>
        </div>
        <SessionContent />
      </div>
      <SessionEditor
        session={editingSession}
        isOpen={isEditorOpen}
        onSave={handleSaveSession}
        onCancel={() => {
          setIsEditorOpen(false);
          setEditingSession(undefined);
        }}
      />
    </>
  );
};
