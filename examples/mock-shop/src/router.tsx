import { createBrowserRouter } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import ProductList from "./pages/ProductList";
import ProductDetail from "./pages/ProductDetail";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Orders from "./pages/Orders";
import AdminDashboard from "./pages/AdminDashboard";
import RequireAuth from "./lib/RequireAuth";

export const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/login", element: <Login /> },
  { path: "/products", element: <ProductList /> },
  { path: "/products/:id", element: <ProductDetail /> },
  { path: "/cart", element: <Cart /> },
  {
    path: "/checkout",
    element: (
      <RequireAuth>
        <Checkout />
      </RequireAuth>
    ),
  },
  {
    path: "/orders",
    element: (
      <RequireAuth>
        <Orders />
      </RequireAuth>
    ),
  },
  {
    path: "/admin",
    element: (
      <RequireAuth role="admin">
        <AdminDashboard />
      </RequireAuth>
    ),
  },
]);
