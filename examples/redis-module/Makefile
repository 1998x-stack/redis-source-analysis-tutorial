CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror
REDIS_SRC ?= ../../.deps/redis-724/src
TARGET := countermod.so

.PHONY: all clean
all: $(TARGET)

$(TARGET): counter_module.c
	$(CC) $(CFLAGS) -fPIC -shared -I$(REDIS_SRC) -o $@ $<

clean:
	rm -f $(TARGET)
