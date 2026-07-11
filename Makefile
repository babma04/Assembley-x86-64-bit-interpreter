CC = gcc
CFLAGS = -O3 -fPIC -I./execution/include
LDFLAGS = -shared

# == Directories ====

SRC_DIR = execution/src
INC_DIR = execution/include
LIB_DIR = lib
BUILD_DIR = build

# Note: Your image shows the folder is named "exectution_tests" (with an extra 't').
# Ensure this variable exactly matches the folder name in your system!
TEST_DIR = tests/exectution_tests
TEST_BUILD_DIR = tests/build
TEST_BIN_DIR = tests/bin

# == Targets ========

# Name of the shared library
SHARED_LIB = $(LIB_DIR)/libexecution.so

# Find all .c files in src/
SRCS = $(wildcard $(SRC_DIR)/*.c)
# Place .o files in the build/ folder
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

# Find all .c files in tests/
TEST_SRCS = $(wildcard $(TEST_DIR)/*.c)
# Create executable targets for each test in tests/bin/
TEST_BINS = $(TEST_SRCS:$(TEST_DIR)/%.c=$(TEST_BIN_DIR)/%)


# == Rules ==========

.PHONY: all directories clean test

all: directories $(SHARED_LIB) $(TEST_BINS)

directories:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(TEST_BUILD_DIR)
	@mkdir -p $(TEST_BIN_DIR)

# Rule to build the shared library
$(SHARED_LIB): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

# Rule to compile execution .c to .o
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Rule to compile AND link test executables against the shared library
$(TEST_BIN_DIR)/%: $(TEST_DIR)/%.c $(SHARED_LIB)
	$(CC) -O3 -I./execution/include $< -o $@ -L$(LIB_DIR) -lexecution -Wl,-rpath=$$(pwd)/$(LIB_DIR)

test: all
	@echo "Running tests..."
	@for test in $(TEST_BINS); do \
		echo "=> Executing $$test"; \
		./$$test || exit 1; \
	done

clean:
	rm -rf $(BUILD_DIR)/* $(LIB_DIR)/*
	@echo "Cleaned execution build and lib folders."
	rm -rf $(TEST_BUILD_DIR)/* $(TEST_BIN_DIR)/*
	@echo "Cleaned test build and bin folders."