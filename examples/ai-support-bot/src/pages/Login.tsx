import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [email, setEmail] = useState("");
  const navigate = useNavigate();

  async function login() {
    if (!email) {
      alert("이메일을 입력해주세요.");
      return;
    }
    // POST /api/auth/login
    await fetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
    navigate("/chat"); // 로그인 완료 → 챗봇으로 이동
  }

  return (
    <section aria-label="로그인">
      <h1>로그인</h1>
      <input placeholder="이메일" value={email} onChange={(e) => setEmail(e.target.value)} />
      <button onClick={login}>로그인</button>
    </section>
  );
}
