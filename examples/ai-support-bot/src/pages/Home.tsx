import { Link } from "react-router-dom";

export default function Home() {
  return (
    <section aria-label="홈">
      <h1>AI 고객지원 챗봇</h1>
      <p>로그인하면 24시간 AI 상담원과 대화할 수 있습니다.</p>
      <Link to="/login">로그인하고 상담 시작하기</Link>
    </section>
  );
}
