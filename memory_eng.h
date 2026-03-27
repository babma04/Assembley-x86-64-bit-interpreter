#ifndef MEMORY_ENG_H
#define MEMORY_ENG_H

#include <stdint.h>
#include <stddef.h>

// --- Constants ---
#define PAGE_SIZE 4096  // 4kb per page
#define MAX_PAGES 512 // 512 * 8 bytes per entry = 4kb tables

// --- Structures ---
// Structure definition of the Table of pages of data
typedef struct {
    void *entries[MAX_PAGES];
} Table;

// --- Core MMU Functions ---
// Used to decompose a virtual address into a physical address, and to read/write memory
uint8_t *decompose_address(uint64_t v_addr, int create_page);

// Single-byte interface
int write_mem(uint64_t v_addr, uint8_t *data, size_t size, int create_page);
int read_mem(uint64_t v_addr, uint8_t *result, size_t size);

// Block interface 
int write_block(uint64_t v_addr, uint8_t *data, size_t size, int create_page);
int read_block(uint64_t v_addr, uint8_t *dest, size_t size);

#endif