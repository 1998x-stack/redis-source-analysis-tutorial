CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
TARGET := mini-redis

.PHONY: all test clean
all: $(TARGET)

$(TARGET): mini-redis.c
	$(CC) $(CFLAGS) -o $@ $<

test: $(TARGET)
	python3 test_mini_redis.py ./$(TARGET)

clean:
	rm -f $(TARGET)
