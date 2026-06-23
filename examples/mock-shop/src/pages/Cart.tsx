import { useNavigate } from "react-router-dom";
import { useCart } from "../lib/cart";

export default function Cart() {
  const { items, removeItem, updateQty, total } = useCart();
  const navigate = useNavigate();

  return (
    <section aria-label="장바구니">
      <h1>장바구니</h1>
      {items.length === 0 && <p>장바구니가 비어 있습니다.</p>}
      {items.map((it) => (
        <div key={it.id}>
          <span>{it.name}</span>
          <input
            type="number"
            min={1}
            max={it.stock}
            value={it.qty}
            onChange={(e) => updateQty(it.id, Number(e.target.value))}
          />
          <button onClick={() => removeItem(it.id)}>삭제</button>
        </div>
      ))}
      <p>합계: {total.toLocaleString()}원</p>
      {/* 빈 장바구니로는 결제 단계 진입 불가 */}
      <button disabled={items.length === 0} onClick={() => navigate("/checkout")}>
        결제하기
      </button>
    </section>
  );
}
