import {
  AgentConfig,
  ModelConfig,
  TeamConfig,
  TerminationConfig,
  ToolConfig,
} from "../../types/datamodel";

export interface GalleryMetadata {
  author: string;
  created_at: string;
  updated_at: string;
  version: string;
  description?: string;
  tags?: string[];
  license?: string;
  homepage?: string;
  category?: string;
  lastSynced?: string;
}

export interface Gallery {
  id: string;
  name: string;
  url?: string;
  metadata: GalleryMetadata;
  items: {
    teams: TeamConfig[];
    components: {
      agents: AgentConfig[];
      models: ModelConfig[];
      tools: ToolConfig[];
      terminations: TerminationConfig[];
    };
  };
}

export interface GalleryAPI {
  listGalleries: () => Promise<Gallery[]>;
  getGallery: (id: string) => Promise<Gallery>;
  createGallery: (gallery: Gallery) => Promise<Gallery>;
  updateGallery: (gallery: Gallery) => Promise<Gallery>;
  deleteGallery: (id: string) => Promise<void>;
}
