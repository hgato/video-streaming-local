import { Routes, Route, Link, useNavigate } from "react-router-dom";
import { useState, useCallback, useEffect } from "react";
import { io } from "socket.io-client";
import Register from "./pages/Register";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Video from "./pages/Video";
import { setOnAuthFailure } from "./api";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [email, setEmail] = useState(localStorage.getItem("email") || "");
  const [socket, setSocket] = useState(null);
  const navigate = useNavigate();

  const handleLogin = useCallback(
    (accessToken, refreshToken, userEmail) => {
      setToken(accessToken);
      setEmail(userEmail);
      localStorage.setItem("token", accessToken);
      localStorage.setItem("refreshToken", refreshToken);
      localStorage.setItem("email", userEmail);
      navigate("/");
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

  useEffect(() => {
    if (!token) {
      setSocket((prev) => {
        if (prev) prev.disconnect();
        return null;
      });
      return;
    }

    const s = io("/", {
      path: "/api/ws/socket.io",
      query: { jwt: token },
      transports: ["polling", "websocket"],
    });
    setSocket(s);

    return () => {
      s.disconnect();
    };
  }, [token]);

  return (
    <>
      <nav>
        {token && <Link to="/">Home</Link>}
        {!token && <Link to="/login">Login</Link>}
        {!token && <Link to="/register">Register</Link>}
        <span className="spacer" />
        {email && <span className="user-info">{email}</span>}
        {token && (
          <a href="#" onClick={handleLogout}>
            Logout
          </a>
        )}
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/videos/:id" element={<Video socket={socket} />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login onLogin={handleLogin} />} />
      </Routes>
    </>
  );
}
