export type UiLanguage = "en" | "vi";

export function detectInputLanguage(value: string): UiLanguage {
  const lowerValue = value.toLowerCase();
  const hasVietnameseDiacritics =
    /[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i.test(
      value,
    );
  const commonVietnameseWords = [
    "một",
    "người",
    "câu chuyện",
    "gia đình",
    "cha",
    "mẹ",
    "con",
    "trước khi",
    "rời",
    "việt nam",
    "muốn",
  ];

  if (hasVietnameseDiacritics) {
    return "vi";
  }

  return commonVietnameseWords.some((word) => lowerValue.includes(word)) ? "vi" : "en";
}
