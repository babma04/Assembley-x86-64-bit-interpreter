CC = gcc
CFLAGS = -O3 -fPIC -I./include
LDFLAGS = -shared

SRC_DIR = src
INC_DIR = include
LIB_DIR = lib
BUILD_DIR = build

TARGET = $(LIB_DIR)/libmmu.so

# Find all .c files in src/
SRCS = $(wildcard $(SRC_DIR)/*.c)
# Place .o files in the build/ folder instead of src/
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

all: directories $(TARGET)

directories:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(BUILD_DIR)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

# Rule to compile .c to .o and put them in build/
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR) $(LIB_DIR)
	@echo "Cleaned build and lib folders."

.PHONY: all directories clean