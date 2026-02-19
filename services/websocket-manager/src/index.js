const http = require("http");
const { Kafka } = require("kafkajs");
const Redis = require("ioredis");

const PORT = process.env.PORT || 3001;
const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";
const KAFKA_BOOTSTRAP_SERVERS = process.env.KAFKA_BOOTSTRAP_SERVERS || "kafka:9092";
const WEBSOCKET_PORT = process.env.WEBSOCKET_PORT || 3000;
const KEY_PREFIX = "ws:user:";

const NOTIFICATIONS_TOPIC = "websocket-notifications.post";

const redis = new Redis(REDIS_URL);

const kafka = new Kafka({
  clientId: "websocket-manager",
  brokers: KAFKA_BOOTSTRAP_SERVERS.split(","),
});
const kafkaConsumer = kafka.consumer({ groupId: "websocket-manager" });

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

function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const data = JSON.stringify(body);
    const req = http.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || 80,
        path: parsed.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(data),
        },
      },
      (res) => {
        res.on("data", () => {});
        res.on("end", () => resolve(res.statusCode));
      }
    );
    req.on("error", reject);
    req.write(data);
    req.end();
  });
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

async function startKafkaConsumer() {
  await kafkaConsumer.connect();
  await kafkaConsumer.subscribe({ topic: NOTIFICATIONS_TOPIC, fromBeginning: false });
  await kafkaConsumer.run({
    eachMessage: async ({ message }) => {
      const payload = JSON.parse(message.value.toString());
      const { user_id, video_id, manifest_url } = payload;

      const websocketIp = await redis.get(`${KEY_PREFIX}${user_id}`);
      if (!websocketIp) {
        console.log(`[notification] user=${user_id} not connected, skipping`);
        return;
      }

      try {
        await httpPost(`http://${websocketIp}:${WEBSOCKET_PORT}/send`, {
          user_id,
          event: "video:ready",
          data: { video_id, manifest_url },
        });
        console.log(`[notification] sent video:ready to user=${user_id}`);
      } catch (err) {
        console.error(`[notification] failed to deliver to user=${user_id}:`, err.message);
      }
    },
  });
  console.log(`Kafka consumer subscribed to ${NOTIFICATIONS_TOPIC}`);
}

server.listen(PORT, async () => {
  console.log(`WebSocket Manager service listening on port ${PORT}`);
  try {
    await startKafkaConsumer();
  } catch (err) {
    console.error("Failed to start Kafka consumer:", err);
  }
});
