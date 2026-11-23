import { createBrowserRouter } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import AdminEvalDashboard from "./pages/AdminEvalDashboard";
import RequireAuth from "./lib/RequireAuth";

export const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/login", element: <Login /> },
  {
    path: "/chat",
    element: (
      <RequireAuth>
        <Chat />
      </RequireAuth>
    ),
  },
  {
    path: "/admin/evals",
    element: (
      <RequireAuth role="admin">
        <AdminEvalDashboard />
      </RequireAuth>
    ),
  },
]);
