package queue

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

type Queue interface {
	Enqueue(ctx context.Context, runID string) error
	Dequeue(ctx context.Context) (string, error)
}

type RedisQueue struct {
	client    *redis.Client
	queueName string
	chanQueue chan string
}

func NewRedisQueue(redisURL, queueName string) *RedisQueue {
	if queueName == "" {
		queueName = "eval_mcp:runs"
	}

	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Printf("Invalid REDIS_URL '%s', using channel fallback: %v", redisURL, err)
		return &RedisQueue{
			chanQueue: make(chan string, 1000),
		}
	}

	rdb := redis.NewClient(opts)
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Printf("Redis ping failed (%s), using in-memory channel queue: %v", redisURL, err)
		return &RedisQueue{
			chanQueue: make(chan string, 1000),
		}
	}

	log.Printf("Connected to Redis queue: %s", queueName)
	return &RedisQueue{
		client:    rdb,
		queueName: queueName,
	}
}

func (q *RedisQueue) Enqueue(ctx context.Context, runID string) error {
	if q.client != nil {
		return q.client.RPush(ctx, q.queueName, runID).Err()
	}
	select {
	case q.chanQueue <- runID:
		return nil
	default:
		return fmt.Errorf("queue full")
	}
}

func (q *RedisQueue) Dequeue(ctx context.Context) (string, error) {
	if q.client != nil {
		res, err := q.client.BLPop(ctx, 2*time.Second, q.queueName).Result()
		if err != nil {
			if err == redis.Nil {
				return "", nil
			}
			return "", err
		}
		if len(res) >= 2 {
			return res[1], nil
		}
		return "", nil
	}

	select {
	case runID := <-q.chanQueue:
		return runID, nil
	case <-time.After(500 * time.Millisecond):
		return "", nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}
