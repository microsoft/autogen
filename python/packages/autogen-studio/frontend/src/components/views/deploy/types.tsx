export interface Guide {
  id: string;
  title: string;
  type: "python" | "docker" | "cloud";
}

export const defaultGuides: Guide[] = [
  {
    id: "python-setup",
    title: "Python",
    type: "python",
  },
  {
    id: "docker-setup",
    title: "Docker",
    type: "docker",
  },
  // {
  //   id: "cloud-deploy",
  //   title: "Cloud",
  //   type: "cloud",
  // },
];
