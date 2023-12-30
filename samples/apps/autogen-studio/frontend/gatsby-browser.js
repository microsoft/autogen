import "antd/dist/reset.css";
import "./src/styles/global.css";

import AuthProvider from "./src/hooks/provider";

export const wrapRootElement = AuthProvider;
