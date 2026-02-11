const http = require("http");

function httpRequest(method, url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const options = {
      hostname: parsed.hostname,
      port: parsed.port,
      path: parsed.pathname,
      method,
      headers: { "Content-Type": "application/json" },
    };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve({ statusCode: res.statusCode, body: data }));
    });

    req.on("error", (err) => reject(err));

    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

function registerHandlers(io, socket, userSockets, config) {
  const { id: userId, email } = socket.data.user;

  console.log(`[connect] socket=${socket.id} user=${userId} email=${email}`);

  userSockets.set(userId, socket.id);

  // Register with websocket-manager (fire-and-forget)
  httpRequest("POST", `${config.MANAGER_URL}/register`, {
    user_id: userId,
    websocket_ip: config.WEBSOCKET_HOST,
  }).then(() => {
    console.log(`[registered] user=${userId}`)
  }).catch((err) => {
    console.error(`[register error] user=${userId}`, err.message);
  });

  socket.on("message", (data) => {
    console.log(`[message] socket=${socket.id} user=${userId} data=`, data);
    socket.emit("message", {
      from: userId,
      data,
      timestamp: Date.now(),
    });
  });

  socket.on("disconnect", (reason) => {
    console.log(
      `[disconnect] socket=${socket.id} user=${userId} reason=${reason}`
    );

    userSockets.delete(userId);

    // Unregister from websocket-manager (fire-and-forget)
    httpRequest("DELETE", `${config.MANAGER_URL}/unregister/${encodeURIComponent(userId)}`).catch(
      (err) => {
        console.error(`[unregister error] user=${userId}`, err.message);
      }
    );
  });
}

module.exports = { registerHandlers };
