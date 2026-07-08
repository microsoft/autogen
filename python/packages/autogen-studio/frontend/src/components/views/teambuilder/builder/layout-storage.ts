import { Component, ComponentConfig } from "../../../types/datamodel";
import { CustomNode } from "./types";

interface Position {
  x: number;
  y: number;
}

interface StoredNodePosition {
  position: Position;
  isUserPositioned: boolean;
  timestamp: number;
}

interface LayoutStorage {
  [teamId: string]: {
    [componentKey: string]: StoredNodePosition;
  };
}

const LAYOUT_STORAGE_KEY = "teambuilder_layout";
const STORAGE_VERSION = 1;
const MAX_STORAGE_AGE = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds

// Simple hash function for component config
const hashConfig = (config: any): string => {
  const str = JSON.stringify(config);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return hash.toString(36);
};

// Generate stable key for a component
export const generateComponentKey = (
  component: Component<ComponentConfig>
): string => {
  const configHash = hashConfig(component.config);
  const label = component.label || component.component_type;
  return `${component.component_type}_${label}_${configHash}`;
};

// Get layout storage from localStorage
const getLayoutStorage = (): LayoutStorage => {
  try {
    const stored = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!stored) return {};

    const parsed = JSON.parse(stored);
    if (parsed.version !== STORAGE_VERSION) {
      // Version mismatch, clear storage
      localStorage.removeItem(LAYOUT_STORAGE_KEY);
      return {};
    }

    return parsed.data || {};
  } catch (error) {
    console.warn("Failed to parse layout storage:", error);
    localStorage.removeItem(LAYOUT_STORAGE_KEY);
    return {};
  }
};

// Save layout storage to localStorage
const saveLayoutStorage = (storage: LayoutStorage): void => {
  try {
    const toStore = {
      version: STORAGE_VERSION,
      data: storage,
    };
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(toStore));
  } catch (error) {
    console.warn("Failed to save layout storage:", error);
  }
};

// Clean up old entries
const cleanupOldEntries = (storage: LayoutStorage): LayoutStorage => {
  const now = Date.now();
  const cleaned: LayoutStorage = {};

  for (const [teamId, teamLayout] of Object.entries(storage)) {
    const cleanedTeamLayout: { [key: string]: StoredNodePosition } = {};

    for (const [componentKey, position] of Object.entries(teamLayout)) {
      if (now - position.timestamp < MAX_STORAGE_AGE) {
        cleanedTeamLayout[componentKey] = position;
      }
    }

    if (Object.keys(cleanedTeamLayout).length > 0) {
      cleaned[teamId] = cleanedTeamLayout;
    }
  }

  return cleaned;
};

// Save node position to storage
export const saveNodePosition = (
  teamId: string,
  component: Component<ComponentConfig>,
  position: Position,
  isUserPositioned: boolean = true
): void => {
  const componentKey = generateComponentKey(component);
  let storage = getLayoutStorage();

  // Clean up old entries periodically
  storage = cleanupOldEntries(storage);

  if (!storage[teamId]) {
    storage[teamId] = {};
  }

  storage[teamId][componentKey] = {
    position,
    isUserPositioned,
    timestamp: Date.now(),
  };

  saveLayoutStorage(storage);
};

// Get stored position for a component
export const getStoredPosition = (
  teamId: string,
  component: Component<ComponentConfig>
): StoredNodePosition | null => {
  const componentKey = generateComponentKey(component);
  const storage = getLayoutStorage();

  return storage[teamId]?.[componentKey] || null;
};

// Check if a component has a user-positioned stored position
export const isComponentUserPositioned = (
  teamId: string,
  component: Component<ComponentConfig>
): boolean => {
  const stored = getStoredPosition(teamId, component);
  return stored?.isUserPositioned || false;
};

// Clear all layout storage for a specific team
export const clearTeamLayoutStorage = (teamId: string): void => {
  const storage = getLayoutStorage();
  delete storage[teamId];
  saveLayoutStorage(storage);
};

// Clear all layout storage (for logout, etc.)
export const clearAllLayoutStorage = (): void => {
  localStorage.removeItem(LAYOUT_STORAGE_KEY);
};

// Mark a node as user-positioned in storage
export const markNodeAsUserPositioned = (
  teamId: string,
  node: CustomNode,
  position: Position
): void => {
  saveNodePosition(teamId, node.data.component, position, true);
};

// Clear user-positioned flag for a team (for auto-layout)
export const clearUserPositionedFlags = (teamId: string): void => {
  const storage = getLayoutStorage();
  const teamLayout = storage[teamId];

  if (teamLayout) {
    for (const componentKey in teamLayout) {
      teamLayout[componentKey].isUserPositioned = false;
    }
    saveLayoutStorage(storage);
  }
};

// Get all user-positioned component keys for a team
export const getUserPositionedComponentKeys = (teamId: string): Set<string> => {
  const storage = getLayoutStorage();
  const teamLayout = storage[teamId];
  const userPositioned = new Set<string>();

  if (teamLayout) {
    for (const [componentKey, position] of Object.entries(teamLayout)) {
      if (position.isUserPositioned) {
        userPositioned.add(componentKey);
      }
    }
  }

  return userPositioned;
};
