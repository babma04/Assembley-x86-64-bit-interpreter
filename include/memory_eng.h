#ifndef MEMORY_ENG_H
#define MEMORY_ENG_H

#include <stdint.h>
#include <stddef.h>

// Compilation command: gcc -O3 -shared -o libmmu.so -fPIC memory_eng.c 

// Prototypes
int write_mem(uint64_t v_addr, uint8_t *data, size_t size, int create_page);
int read_mem(uint64_t v_addr, uint8_t *result, size_t size);

#endif // MEMORY_ENG_H