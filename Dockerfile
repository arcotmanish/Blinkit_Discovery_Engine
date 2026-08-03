FROM node:20-bullseye-slim

# Install Python and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Setup Python Backend
COPY backend/requirements.txt /app/backend/
RUN pip3 install -r /app/backend/requirements.txt
COPY backend /app/backend

# Setup Node.js Frontend
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm install
COPY frontend /app/frontend

# Provide build-time variables for Next.js
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY

RUN npm run build

# Expose port and start Next.js
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "start"]
