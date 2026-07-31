# Build stage
FROM golang:1.24-alpine AS builder
ENV GOTOOLCHAIN=auto

WORKDIR /app

# Install ca-certificates and git
RUN apk add --no-cache ca-certificates git

# Copy module files and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build statically linked binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/eval-mcp ./cmd/eval-mcp

# Final runtime stage
FROM alpine:3.21

WORKDIR /app

RUN apk add --no-cache ca-certificates tzdata

COPY --from=builder /app/eval-mcp /app/eval-mcp

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["/app/eval-mcp"]
CMD ["api"]
