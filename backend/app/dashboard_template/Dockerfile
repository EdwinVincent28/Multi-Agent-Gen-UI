FROM us-central1-docker.pkg.dev/gen-ui-swarm/gen-ui-repo/gen-ui-base:latest as build
WORKDIR /app

COPY . .
RUN npm run build

# Stage 2: Serve the static files with Nginx (Lightweight & Fast)
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]