import "@refinedev/mui";

export interface CustomTheme {
  // Add custom variables here like below:
  // status: {
  //   danger: string;
  // };
}

declare module "@refinedev/mui" {
  interface Theme extends import("@refinedev/mui").Theme, CustomTheme {}
  interface ThemeOptions
    extends import("@refinedev/mui").ThemeOptions,
      CustomTheme {}
}
