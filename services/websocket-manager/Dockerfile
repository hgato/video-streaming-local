FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* /app/

RUN npm install --omit=dev

COPY src /app/src

EXPOSE 3001

CMD ["node", "src/index.js"]
