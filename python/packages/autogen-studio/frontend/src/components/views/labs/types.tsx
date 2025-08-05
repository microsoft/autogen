export interface Lab {
  id: string;
  title: string;
  type: "python" | "docker" | "cloud";
}

export const defaultLabs: Lab[] = [
  // {
  //   id: "component-builder",
  //   title: "Component Builder",
  //   type: "python",
  // },
  {
    id: "tool-maker",
    title: "Tool Maker",
    type: "python",
  },
];
