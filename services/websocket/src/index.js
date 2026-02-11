const http = require("http");
const { Server } = require("socket.io");
const authMiddleware = require("./middleware/auth");
const { registerHandlers } = require("./handlers");

const PORT = process.env.PORT || 3000;
const WEBSOCKET_HOST = process.env.WEBSOCKET_HOST || "localhost";
const MANAGER_URL = process.env.MANAGER_URL || "http://websocket-manager:3001";

const userSockets = new Map();

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on("error", reject);
  });
}

const server = http.createServer(async (req, res) => {
  if (req.url === "/health" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  if (req.url === "/send" && req.method === "POST") {
    try {
      const { user_id, event, data } = await parseBody(req);
      if (!user_id || !event) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "user_id and event are required" }));
        return;
      }

      const socketId = userSockets.get(user_id);
      if (!socketId) {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "user not connected to this server" }));
        return;
      }

      const targetSocket = io.sockets.sockets.get(socketId);
      if (!targetSocket) {
        userSockets.delete(user_id);
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "socket not found" }));
        return;
      }

      targetSocket.emit(event, data);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
    } catch (err) {
      console.error("[send error]", err);
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "internal server error" }));
    }
    return;
  }

  res.writeHead(404);
  res.end();
});

const io = new Server(server, {
  cors: {
    origin: "*",
  },
  transports: ["polling", "websocket"],
});

io.use(authMiddleware);

const config = { WEBSOCKET_HOST, MANAGER_URL };

io.on("connection", (socket) => {
  registerHandlers(io, socket, userSockets, config);
});

server.listen(PORT, () => {
  console.log(`WebSocket service listening on port ${PORT}`);
});
