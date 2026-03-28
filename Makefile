# --- Compiler and Flags ---
CC = gcc
# -O3: Maximum optimization for your Ryzen 5
# -fPIC: Position Independent Code (required for shared libraries)
# -I./include: Tells the compiler to look for your .h files in the include folder
CFLAGS = -O3 -fPIC -I./include
LDFLAGS = -shared

# --- Directories ---
SRC_DIR = src
INC_DIR = include
LIB_DIR = lib

# --- Target Library Name ---
TARGET = $(LIB_DIR)/libmmu.so

# --- Source and Object Files ---
# This automatically finds all .c files in your src/ folder
SRCS = $(wildcard $(SRC_DIR)/*.c)
# This converts the .c list into a .o (object) list in the same folder
OBJS = $(SRCS:.c=.o)

# --- Rules ---

# Default rule: Build the folders and then the library
all: directories $(TARGET)

# Create the /lib folder if it doesn't exist
directories:
	@mkdir -p $(LIB_DIR)

# Link the object files into the final .so library
$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $^

# Compile each .c file into a .o file
# It stays in the /src folder temporarily during the build
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up build files (use 'make clean')
clean:
	rm -f $(SRC_DIR)/*.o $(TARGET)
	@echo "Cleaned up object files and library."

.PHONY: all directories clean
