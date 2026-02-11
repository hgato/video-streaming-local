function registerHandlers(io, socket) {
  const { id: userId, email } = socket.data.user;

  console.log(`[connect] socket=${socket.id} user=${userId} email=${email}`);

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
  });
}

module.exports = { registerHandlers };
