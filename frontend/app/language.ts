export type UiLanguage = "en" | "vi";
export type ResponseLanguage = "auto" | "vi" | "en";
export const responseLanguageLabels: Record<ResponseLanguage, string> = {
  auto: "Tự nhận diện (Việt / Anh)", vi: "Tiếng Việt", en: "Tiếng Anh",
};
