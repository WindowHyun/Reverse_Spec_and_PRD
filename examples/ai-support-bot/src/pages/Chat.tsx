import { useState } from "react";
import { useAuth } from "../lib/auth";
import { validateMessage } from "../lib/validate";

export default function Chat() {
  const { user } = useAuth();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);

  async function send() {
    const err = validateMessage(input);
    if (err) {
      alert(err);
      return;
    }
    // POST /api/chat
    const res = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ userId: user?.id, message: input }),
    });
    const data = await res.json();
    setMessages((prev) => [...prev, { role: "user", content: input }, { role: "bot", content: data.reply }]);
    setInput("");
  }

  return (
    <section aria-label="상담 채팅">
      <h1>AI 상담</h1>
      {messages.length === 0 && <p>아직 대화가 없습니다. 궁금한 점을 물어보세요.</p>}
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m.role === "user" ? "나" : "상담원"}: {m.content}</li>
        ))}
      </ul>
      <input placeholder="메시지를 입력하세요" value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={send} disabled={!input.trim()}>전송</button>
    </section>
  );
}
