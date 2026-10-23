import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import enUS from "./locales/en-US/translation.json";
import zhCN from "./locales/zh-CN/translation.json";

const savedLang =
  typeof window !== "undefined"
    ? localStorage.getItem("autogen-lang") || "en-US"
    : "en-US";

i18n.use(initReactI18next).init({
  resources: {
    "en-US": { translation: enUS },
    "zh-CN": { translation: zhCN },
  },
  lng: savedLang,
  fallbackLng: "en-US",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
