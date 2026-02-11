const http = require("http");
const Redis = require("ioredis");

const PORT = process.env.PORT || 3001;
const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";
const KEY_PREFIX = "ws:user:";

const redis = new Redis(REDIS_URL);

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

function json(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  try {
    // GET /health
    if (req.method === "GET" && req.url === "/health") {
      const pong = await redis.ping();
      json(res, 200, { status: "ok", redis: pong });
      return;
    }

    // POST /register
    if (req.method === "POST" && req.url === "/register") {
      const { user_id, websocket_ip } = await parseBody(req);
      if (!user_id || !websocket_ip) {
        json(res, 400, { error: "user_id and websocket_ip are required" });
        return;
      }
      await redis.set(`${KEY_PREFIX}${user_id}`, websocket_ip);
      json(res, 200, { ok: true });
      return;
    }

    // GET /lookup/:user_id
    const lookupMatch = req.method === "GET" && req.url.match(/^\/lookup\/(.+)$/);
    if (lookupMatch) {
      const userId = decodeURIComponent(lookupMatch[1]);
      const websocketIp = await redis.get(`${KEY_PREFIX}${userId}`);
      if (!websocketIp) {
        json(res, 404, { error: "user not connected" });
        return;
      }
      json(res, 200, { user_id: userId, websocket_ip: websocketIp });
      return;
    }

    // DELETE /unregister/:user_id
    const unregisterMatch =
      req.method === "DELETE" && req.url.match(/^\/unregister\/(.+)$/);
    if (unregisterMatch) {
      const userId = decodeURIComponent(unregisterMatch[1]);
      await redis.del(`${KEY_PREFIX}${userId}`);
      json(res, 200, { ok: true });
      return;
    }

    res.writeHead(404);
    res.end();
  } catch (err) {
    console.error("[error]", err);
    json(res, 500, { error: "internal server error" });
  }
});

server.listen(PORT, () => {
  console.log(`WebSocket Manager service listening on port ${PORT}`);
});
