const http = require("http");
const { Server } = require("socket.io");
const authMiddleware = require("./middleware/auth");
const { registerHandlers } = require("./handlers");

const PORT = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  if (req.url === "/health" && req.method === "GET") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
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

io.on("connection", (socket) => {
  registerHandlers(io, socket);
});

server.listen(PORT, () => {
  console.log(`WebSocket service listening on port ${PORT}`);
});
