import { GOLDEN_CASES } from "../evals/chatbot.eval";

export default function AdminEvalDashboard() {
  return (
    <section aria-label="eval 리포트">
      <h1>챗봇 품질 eval 리포트</h1>
      <p>골든셋 {GOLDEN_CASES.length}건 기준 최근 실행 결과입니다.</p>
      <ul>
        {GOLDEN_CASES.map((c, i) => (
          <li key={i}>{c.input} → {c.expectedTopic}</li>
        ))}
      </ul>
    </section>
  );
}
