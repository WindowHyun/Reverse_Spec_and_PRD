import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCart } from "../lib/cart";

const SHIPPING_FEE = 3000;
const FREE_SHIPPING_THRESHOLD = 50000;

export default function Checkout() {
  const { items, total, clear } = useCart();
  const [address, setAddress] = useState("");
  const [pay, setPay] = useState("card");
  const navigate = useNavigate();

  // 5만원 이상 구매 시 무료배송 정책
  const shipping = total >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FEE;
  const grandTotal = total + shipping;

  async function placeOrder() {
    if (!address) {
      alert("배송지를 입력해주세요.");
      return;
    }
    // POST /api/orders
    await fetch("/api/orders", {
      method: "POST",
      body: JSON.stringify({ items, address, pay, grandTotal }),
    });
    clear();
    navigate("/orders"); // 주문 완료 → 주문내역으로 이동
  }

  return (
    <section aria-label="결제">
      <h1>결제</h1>
      <input placeholder="배송지" value={address} onChange={(e) => setAddress(e.target.value)} />
      <select value={pay} onChange={(e) => setPay(e.target.value)}>
        <option value="card">신용카드</option>
        <option value="bank">계좌이체</option>
      </select>
      <p>상품금액: {total.toLocaleString()}원</p>
      <p>배송비: {shipping.toLocaleString()}원 {shipping === 0 && "(무료배송)"}</p>
      <p>결제금액: {grandTotal.toLocaleString()}원</p>
      <button onClick={placeOrder}>{grandTotal.toLocaleString()}원 결제</button>
    </section>
  );
}
