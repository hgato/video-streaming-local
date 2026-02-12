import { Routes, Route, Link, useNavigate } from "react-router-dom";
import { useState, useCallback, useEffect } from "react";
import Register from "./pages/Register";
import Login from "./pages/Login";
import WebSocketTest from "./pages/WebSocketTest";
import { setOnAuthFailure } from "./api";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [email, setEmail] = useState(localStorage.getItem("email") || "");
  const navigate = useNavigate();

  const handleLogin = useCallback(
    (accessToken, refreshToken, userEmail) => {
      setToken(accessToken);
      setEmail(userEmail);
      localStorage.setItem("token", accessToken);
      localStorage.setItem("refreshToken", refreshToken);
      localStorage.setItem("email", userEmail);
      navigate("/ws");
    },
    [navigate]
  );

  const handleLogout = useCallback(() => {
    setToken("");
    setEmail("");
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("email");
    navigate("/login");
  }, [navigate]);

  useEffect(() => {
    setOnAuthFailure(handleLogout);
  }, [handleLogout]);

  return (
    <>
      <nav>
        <Link to="/register">Register</Link>
        <Link to="/login">Login</Link>
        {token && <Link to="/ws">WebSocket</Link>}
        <span className="spacer" />
        {email && <span className="user-info">{email}</span>}
        {token && (
          <a href="#" onClick={handleLogout}>
            Logout
          </a>
        )}
      </nav>
      <Routes>
        <Route path="/" element={<Login onLogin={handleLogin} />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login onLogin={handleLogin} />} />
        <Route path="/ws" element={<WebSocketTest token={token} />} />
      </Routes>
    </>
  );
}
