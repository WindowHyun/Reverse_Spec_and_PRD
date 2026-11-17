// 챗봇 응답 품질 골든셋 — CI에서 모델/프롬프트 변경 시 재실행해 회귀를 확인한다.
export const GOLDEN_CASES = [
  { input: "배송은 얼마나 걸리나요?", expectedTopic: "배송" },
  { input: "환불하고 싶어요", expectedTopic: "환불" },
];
