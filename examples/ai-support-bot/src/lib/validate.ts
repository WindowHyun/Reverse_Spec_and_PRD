const MAX_MESSAGE_LENGTH = 1000;

export function validateMessage(text: string): string | null {
  if (!text.trim()) {
    return "메시지를 입력해주세요.";
  }
  if (text.length > MAX_MESSAGE_LENGTH) {
    return "메시지는 1000자를 넘을 수 없습니다.";
  }
  return null;
}
