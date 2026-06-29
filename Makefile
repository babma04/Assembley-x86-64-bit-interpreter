CC = gcc
CFLAGS = -O3 -fPIC -I./execution/include
LDFLAGS = -shared

// == Directories ====

SRC_DIR = execution/src
INC_DIR = execution/include
LIB_DIR = lib
BUILD_DIR = build

DIR_TARGET = $(LIB_DIR)

// == TESTS ==========

TEST_DIR = tests/execution_tests
TEST_LIB_DIR = tests/lib
TEST_BUILD_DIR = tests/build

TEST_TARGET = $(TEST_LIB_DIR)


// == Rules ==========

# Find all .c files in src/
SRCS = $(wildcard $(SRC_DIR)/*.c)
# Place .o files in the build/ folder instead of src/
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(BUILD_DIR)/%.o)

# FInd all .c files in tests/
TEST_SRCS = $(wildcard $(TEST_DIR)/*.c)
# Place .o files in the tests/build/ folder instead of tests/
TEST_OBJS = $(TEST_SRCS:$(TEST_DIR)/%.c=$(TEST_BUILD_DIR)/%.o)

all: directories $(DIR_TARGET) && $(TEST_TARGET)

directories:
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(BUILD_DIR)
	@mkdir -p $(TEST_LIB_DIR)
	@mkdir -p $(TEST_BUILD_DIR)

$(DIR_TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

# Rule to compile .c to .o and put them in build/
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

$(TEST_BUILD_DIR)/%.o: $(TEST_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

test: $(TEST_TARGET)
	@echo "Running tests..."
	./tests/execution_tests/run_tests.sh


clean:
	rm -rf $(BUILD_DIR) $(LIB_DIR)
	@echo "Cleaned build and lib folders."

	rm -rf $(TEST_BUILD_DIR) $(TEST_LIB_DIR)
	@echo "Cleaned test build and test lib folders."

.PHONY: all directories clean test