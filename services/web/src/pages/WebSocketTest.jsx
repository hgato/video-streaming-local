import { useState, useEffect, useRef, useCallback } from "react";
import { io } from "socket.io-client";

export default function WebSocketTest({ token }) {
  const [logs, setLogs] = useState([]);
  const [message, setMessage] = useState("");
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const logEndRef = useRef(null);

  const addLog = useCallback((type, text) => {
    const ts = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { ts, type, text }]);
  }, []);

  useEffect(() => {
    if (!token) return;

    addLog("info", "Connecting to WebSocket...");

    const socket = io("/", {
      path: "/api/ws/socket.io",
      query: { jwt: token },
      transports: ["polling", "websocket"],
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      addLog("connected", `Connected (socket.id: ${socket.id})`);
    });

    socket.on("message", (data) => {
      addLog(
        "message",
        `Echo from server: ${JSON.stringify(data)}`
      );
    });

    socket.on("connect_error", (err) => {
      addLog("error", `Connection error: ${err.message}`);
    });

    socket.on("disconnect", (reason) => {
      setConnected(false);
      addLog("disconnected", `Disconnected: ${reason}`);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [token, addLog]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  function handleSend(e) {
    e.preventDefault();
    if (!message.trim() || !socketRef.current) return;
    addLog("info", `Sending: ${message}`);
    socketRef.current.emit("message", message);
    setMessage("");
  }

  if (!token) {
    return (
      <div className="page">
        <h1>WebSocket Test</h1>
        <p>Please log in first to test the WebSocket connection.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>WebSocket Test</h1>
      <p>
        Status:{" "}
        <strong className={connected ? "connected" : "disconnected"}>
          {connected ? "Connected" : "Disconnected"}
        </strong>
      </p>

      <div className="log">
        {logs.map((entry, i) => (
          <div key={i} className="entry">
            <span className="ts">{entry.ts}</span>
            <span className={entry.type}>{entry.text}</span>
          </div>
        ))}
        <div ref={logEndRef} />
      </div>

      <form className="ws-controls" onSubmit={handleSend}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type a message..."
          disabled={!connected}
        />
        <button type="submit" disabled={!connected}>
          Send
        </button>
      </form>
    </div>
  );
}
