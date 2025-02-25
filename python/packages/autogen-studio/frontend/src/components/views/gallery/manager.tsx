import React, { useCallback, useEffect, useState, useContext } from "react";
import { message, Modal } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import { galleryAPI } from "./api";
import { GallerySidebar } from "./sidebar";
import { GalleryDetail } from "./detail";
import { GalleryCreateModal } from "./create-modal";
import type { Gallery } from "../../types/datamodel";

export const GalleryManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [galleries, setGalleries] = useState<Gallery[]>([]);
  const [currentGallery, setCurrentGallery] = useState<Gallery | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("gallerySidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  const { user } = useContext(appContext);
  const [messageApi, contextHolder] = message.useMessage();

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("gallerySidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  const fetchGalleries = useCallback(async () => {
    if (!user?.email) return;

    try {
      setIsLoading(true);
      const data = await galleryAPI.listGalleries(user.email);
      setGalleries(data);
      if (!currentGallery && data.length > 0) {
        setCurrentGallery(data[0]);
      }
    } catch (error) {
      console.error("Error fetching galleries:", error);
      messageApi.error("Failed to fetch galleries");
    } finally {
      setIsLoading(false);
    }
  }, [user?.email, currentGallery, messageApi]);

  useEffect(() => {
    fetchGalleries();
  }, [fetchGalleries]);

  // Handle URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const galleryId = params.get("galleryId");

    if (galleryId && !currentGallery) {
      const numericId = parseInt(galleryId, 10);
      if (!isNaN(numericId)) {
        handleSelectGallery(numericId);
      }
    }
  }, []);

  // Update URL when gallery changes
  useEffect(() => {
    if (currentGallery?.id) {
      window.history.pushState(
        {},
        "",
        `?galleryId=${currentGallery.id.toString()}`
      );
    }
  }, [currentGallery?.id]);

  const handleSelectGallery = async (galleryId: number) => {
    if (!user?.email) return;

    if (hasUnsavedChanges) {
      Modal.confirm({
        title: "Unsaved Changes",
        content: "You have unsaved changes. Do you want to discard them?",
        okText: "Discard",
        cancelText: "Go Back",
        onOk: () => {
          switchToGallery(galleryId);
          setHasUnsavedChanges(false);
        },
      });
    } else {
      await switchToGallery(galleryId);
    }
  };

  const switchToGallery = async (galleryId: number) => {
    if (!user?.email) return;

    setIsLoading(true);
    try {
      const data = await galleryAPI.getGallery(galleryId, user.email);
      setCurrentGallery(data);
    } catch (error) {
      console.error("Error loading gallery:", error);
      messageApi.error("Failed to load gallery");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateGallery = async (galleryData: Gallery) => {
    if (!user?.email) return;

    galleryData.user_id = user.email;
    try {
      const savedGallery = await galleryAPI.createGallery(
        galleryData,
        user.email
      );
      setGalleries([savedGallery, ...galleries]);
      setCurrentGallery(savedGallery);
      setIsCreateModalOpen(false);
      messageApi.success("Gallery created successfully");
    } catch (error) {
      console.error("Error creating gallery:", error);
      messageApi.error("Failed to create gallery");
    }
  };

  const handleUpdateGallery = async (updates: Partial<Gallery>) => {
    if (!user?.email || !currentGallery?.id) return;

    try {
      const sanitizedUpdates = {
        ...updates,
        created_at: undefined,
        updated_at: undefined,
      };
      const updatedGallery = await galleryAPI.updateGallery(
        currentGallery.id,
        sanitizedUpdates,
        user.email
      );
      setGalleries(
        galleries.map((g) => (g.id === updatedGallery.id ? updatedGallery : g))
      );
      setCurrentGallery(updatedGallery);
      setHasUnsavedChanges(false);
      messageApi.success("Gallery updated successfully");
    } catch (error) {
      console.error("Error updating gallery:", error);
      messageApi.error("Failed to update gallery");
    }
  };

  const handleDeleteGallery = async (galleryId: number) => {
    if (!user?.email) return;

    try {
      await galleryAPI.deleteGallery(galleryId, user.email);
      setGalleries(galleries.filter((g) => g.id !== galleryId));
      if (currentGallery?.id === galleryId) {
        setCurrentGallery(null);
      }
      messageApi.success("Gallery deleted successfully");
    } catch (error) {
      console.error("Error deleting gallery:", error);
      messageApi.error("Failed to delete gallery");
    }
  };

  const handleSyncGallery = async (galleryId: number) => {
    if (!user?.email) return;

    try {
      setIsLoading(true);
      const gallery = galleries.find((g) => g.id === galleryId);
      if (!gallery?.config.url) return;

      const remoteGallery = await galleryAPI.syncGallery(gallery.config.url);
      await handleUpdateGallery({
        ...remoteGallery,
        id: galleryId,
        config: {
          ...remoteGallery.config,
          metadata: {
            ...remoteGallery.config.metadata,
            lastSynced: new Date().toISOString(),
          },
        },
      });

      messageApi.success("Gallery synced successfully");
    } catch (error) {
      console.error("Error syncing gallery:", error);
      messageApi.error("Failed to sync gallery");
    } finally {
      setIsLoading(false);
    }
  };

  if (!user?.email) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
        Please log in to view galleries
      </div>
    );
  }

  return (
    <div className="relative flex h-full w-full">
      {contextHolder}

      {/* Create Modal */}
      <GalleryCreateModal
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
        onCreateGallery={handleCreateGallery}
      />

      {/* Sidebar */}
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <GallerySidebar
          isOpen={isSidebarOpen}
          galleries={galleries}
          currentGallery={currentGallery}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectGallery={(gallery) => handleSelectGallery(gallery.id!)}
          onCreateGallery={() => setIsCreateModalOpen(true)}
          onDeleteGallery={handleDeleteGallery}
          onSyncGallery={handleSyncGallery}
          isLoading={isLoading}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Galleries</span>
            {currentGallery && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">
                  {currentGallery.config.name}
                </span>
              </>
            )}
          </div>

          {/* Content Area */}
          {isLoading && !currentGallery ? (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              Loading galleries...
            </div>
          ) : currentGallery ? (
            <GalleryDetail
              gallery={currentGallery}
              onSave={handleUpdateGallery}
              onDirtyStateChange={setHasUnsavedChanges}
            />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              Select a gallery from the sidebar or create a new one
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default GalleryManager;
