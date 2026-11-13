import { useTranslation } from "react-i18next";
import { Select } from "antd";

const languages = [
  { value: "en-US", label: "English" },
  { value: "zh-CN", label: "简体中文" },
];

export const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  return (
    <Select
      value={i18n.language}
      options={languages}
      onChange={(lang: string) => {
        i18n.changeLanguage(lang);
        localStorage.setItem("autogen-lang", lang);
      }}
      size="small"
      bordered={false}
      style={{ width: 110 }}
    />
  );
};
