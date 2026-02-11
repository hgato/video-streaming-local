FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* /app/

RUN npm install --omit=dev

COPY src /app/src

EXPOSE 3000

CMD ["node", "src/index.js"]
