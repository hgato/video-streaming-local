const jwt = require("jsonwebtoken");

const JWT_SECRET = process.env.JWT_SECRET;

function authMiddleware(socket, next) {
  const token = socket.handshake.query.jwt;

  if (!token) {
    return next(new Error("Authentication required: no JWT provided"));
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET, {
      algorithms: ["HS256"],
      issuer: "auth",
    });

    socket.data.user = {
      id: payload.id,
      email: payload.email,
      permissions: payload.permissions || [],
    };

    next();
  } catch (err) {
    return next(new Error(`Authentication failed: ${err.message}`));
  }
}

module.exports = authMiddleware;
