import React, { useCallback, useEffect, useState, useContext } from "react";
import { Button, message } from "antd";
import { useConfigStore } from "../../../hooks/store";
import { appContext } from "../../../hooks/provider";
import { sessionAPI } from "./api";
import { SessionEditor } from "./editor";
import type { Session, Team } from "../../types/datamodel";
import ChatView from "./chat/chat";
import { Sidebar } from "./sidebar";
import { teamAPI } from "../teambuilder/api";
import { useGalleryStore } from "../gallery/store";

export const SessionManager: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<Session | undefined>();
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("sessionSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true; // Default value during SSR
  });
  const [messageApi, contextHolder] = message.useMessage();

  const { user } = useContext(appContext);
  const { session, setSession, sessions, setSessions } = useConfigStore();

  const galleryStore = useGalleryStore();

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("sessionSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  const fetchSessions = useCallback(async () => {
    if (!user?.id) return;

    try {
      setIsLoading(true);
      const data = await sessionAPI.listSessions(user.id);
      setSessions(data);

      // Only set first session if there's no sessionId in URL
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get("sessionId");
      if (!session && data.length > 0 && !sessionId) {
        setSession(data[0]);
      }
    } catch (error) {
      console.error("Error fetching sessions:", error);
      messageApi.error("Error loading sessions");
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, setSessions, session, setSession]);

  // Handle initial URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("sessionId");

    if (sessionId && !session) {
      handleSelectSession({ id: parseInt(sessionId) } as Session);
    }
  }, []);

  // Handle browser back/forward
  useEffect(() => {
    const handleLocationChange = () => {
      const params = new URLSearchParams(window.location.search);
      const sessionId = params.get("sessionId");

      if (!sessionId && session) {
        setSession(null);
      }
    };

    window.addEventListener("popstate", handleLocationChange);
    return () => window.removeEventListener("popstate", handleLocationChange);
  }, [session]);

  const handleSaveSession = async (sessionData: Partial<Session>) => {
    if (!user?.id) return;

    try {
      if (sessionData.id) {
        const updated = await sessionAPI.updateSession(
          sessionData.id,
          sessionData,
          user.id
        );
        setSessions(sessions.map((s) => (s.id === updated.id ? updated : s)));
        if (session?.id === updated.id) {
          setSession(updated);
        }
      } else {
        const created = await sessionAPI.createSession(sessionData, user.id);
        setSessions([created, ...sessions]);
        setSession(created);
      }
      setIsEditorOpen(false);
      setEditingSession(undefined);
    } catch (error) {
      messageApi.error("Error saving session");
      console.error(error);
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    if (!user?.id) return;

    try {
      const response = await sessionAPI.deleteSession(sessionId, user.id);
      setSessions(sessions.filter((s) => s.id !== sessionId));
      if (session?.id === sessionId || sessions.length === 0) {
        setSession(sessions[0] || null);
        window.history.pushState({}, "", window.location.pathname); // Clear URL params
      }
      messageApi.success("Session deleted");
    } catch (error) {
      console.error("Error deleting session:", error);
      messageApi.error("Error deleting session");
    }
  };

  const handleQuickStart = async (teamId: number, teamName: string) => {
    if (!user?.id) return;
    try {
      const defaultName = `${teamName.substring(
        0,
        20
      )} - ${new Date().toLocaleString()} Session`;
      const created = await sessionAPI.createSession(
        {
          name: defaultName,
          team_id: teamId,
        },
        user.id
      );

      setSessions([created, ...sessions]);
      setSession(created);
      messageApi.success("Session created!");
    } catch (error) {
      messageApi.error("Error creating session");
    }
  };

  const handleSelectSession = async (selectedSession: Session) => {
    if (!user?.id || !selectedSession.id) return;

    try {
      setIsLoading(true);
      const data = await sessionAPI.getSession(selectedSession.id, user.id);
      if (!data) {
        // Session not found
        messageApi.error("Session not found");
        window.history.pushState({}, "", window.location.pathname); // Clear URL
        if (sessions.length > 0) {
          setSession(sessions[0]); // Fall back to first session
        } else {
          setSession(null);
        }
        return;
      }
      setSession(data);
      window.history.pushState({}, "", `?sessionId=${selectedSession.id}`);
    } catch (error) {
      console.error("Error loading session:", error);
      messageApi.error("Error loading session");
      window.history.pushState({}, "", window.location.pathname); // Clear invalid URL
      if (sessions.length > 0) {
        setSession(sessions[0]); // Fall back to first session
      } else {
        setSession(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Add teams fetching
  const fetchTeams = useCallback(async () => {
    // console.log("Fetching teams", user);
    if (!user?.id) return;

    try {
      setIsLoading(true);
      const teamsData = await teamAPI.listTeams(user.id);
      if (teamsData.length > 0) {
        setTeams(teamsData);
      } else {
        console.log("No teams found, creating default team");
        await galleryStore.fetchGalleries(user.id);
        const defaultGallery = galleryStore.getSelectedGallery();

        const sampleTeam = defaultGallery?.config.components.teams[0];
        console.log("Default Gallery .. manager fetching ", sampleTeam);
        // // If no teams, create a default team
        if (sampleTeam) {
          const teamData: Team = {
            component: sampleTeam,
          };
          const defaultTeam = await teamAPI.createTeam(teamData, user.id);
          console.log("Default team created:", teamData);

          setTeams([defaultTeam]);
        }
      }
    } catch (error) {
      console.error("Error fetching teams:", error);
      messageApi.error("Error loading teams");
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, messageApi]);

  // Fetch teams on mount
  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  return (
    <div className="relative flex h-full w-full">
      {contextHolder}
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <Sidebar
          isOpen={isSidebarOpen}
          teams={teams}
          onStartSession={handleQuickStart}
          sessions={sessions}
          currentSession={session}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectSession={handleSelectSession}
          onEditSession={(session) => {
            setEditingSession(session);
            setIsEditorOpen(true);
          }}
          onDeleteSession={handleDeleteSession}
          isLoading={isLoading}
        />
      </div>

      <div
        className={`flex-1 transition-all -mr-4 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        {session && sessions.length > 0 ? (
          <div className="pl-4">
            {session && <ChatView session={session} />}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-secondary">
            No session selected. Create or select a session from the sidebar.
          </div>
        )}
      </div>

      <SessionEditor
        teams={teams}
        session={editingSession}
        isOpen={isEditorOpen}
        onSave={handleSaveSession}
        onCancel={() => {
          setIsEditorOpen(false);
          setEditingSession(undefined);
        }}
      />
    </div>
  );
};
