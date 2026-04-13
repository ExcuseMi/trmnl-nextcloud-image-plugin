FROM node:24-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY run.js .
CMD ["node", "run.js"]
