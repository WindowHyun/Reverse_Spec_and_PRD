import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  function validate() {
    if (!email) return "이메일을 입력해주세요.";
    if (!/^[^@]+@[^@]+\.[^@]+$/.test(email)) return "올바른 이메일 형식이 아닙니다.";
    if (password.length < 8) return "비밀번호는 8자 이상이어야 합니다.";
    return "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    try {
      await login(email, password); // POST /api/auth/login
      const to = location.state?.from?.pathname || "/products";
      navigate(to, { replace: true });
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="로그인 폼">
      <h1>로그인</h1>
      <input placeholder="이메일" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input
        type="password"
        placeholder="비밀번호 (8자 이상)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <p role="alert">{error}</p>}
      <button type="submit">로그인</button>
    </form>
  );
}
