import { LucideIcon } from "lucide-react";

export interface SettingsSection {
  id: string;
  title: string;
  icon: LucideIcon;
  content: () => JSX.Element;
}
