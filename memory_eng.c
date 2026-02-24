#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

// Compilation command: gcc -O3 -shared -o libmmu.so -fPIC memory_eng.c 

// Constants declarations
#define PAGE_SIZE 4096  // 4kb per page
#define MAX_PAGES 512 // 512 * 8 bytes per entry = 4kb tables

// Structure definition of the Table of pages of data
typedef struct {
    void *entries[MAX_PAGES];  // allocates 8 bytes for the address (that's why void)
} Table;

// Prototypes (Not strictly needed in this case, might remove later)
uint8_t *decompose_address(uint64_t v_addr, int create_page);
void write_mem(uint64_t v_addr, uint8_t value);
int read_mem(uint64_t v_addr, uint8_t *result);

// Initializing Table at NULL and rewrite it as needed using the PML4 reg
Table* CR3 = NULL;

/**
 * Main MMU funion. 
 * Should initialize the Table structure if it's not yet created.
 * Used to handle reads and writes aswell as manage page creation if needed.
 * 
 * @param v_addr Virtual address given by the caller
 * @param create_page Flags for the operation type (0 - for read; 1 - for write)
 * @return Pointer to the physical byte, or NULL if unmapped and create_page is 0
 * @note create_page param affects directly Table structures creation permission. 
 */
uint8_t *decompose_address(uint64_t v_addr, int create_page)
{
    // If the page_dir_root is not yet initialized initialize it
    if (!CR3)
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if (!create_page)
        {
            return NULL;
        }
        // Else allocates a block of memory for a Table structure and starts it out at 0
        CR3 = (Table*)calloc(1, sizeof(Table));
    }

    // Table index and offset extration:
    // Extracts the first 9 bits of the address
    uint64_t pml4 = (v_addr >> 39) & 0x1FF;
    // Extracts the 9 following bits
    uint64_t dir_ptr = (v_addr >> 30) & 0x1FF;
    // Extracts the 9 bits of the Directory of the Table
    uint64_t dir = (v_addr >> 21) & 0x1FF;
    // Ignores the last 12 bits of the address and extracts the 9 bits of the Table index
    uint64_t table = (v_addr >> 12) & 0x1FF;
    // Extracts the last 12 bits of the address
    uint64_t offset = v_addr & 0xFFF;

    // If the first directory level (PML64) is not initialized initializes it
    if (!CR3->entries[pml4])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page)
        {
            return NULL;
        }
        // Else allocates a block of memory for a Table structure and starts it out at 0
        CR3->entries[pml4] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *dir_ptr_pointer = (Table*)CR3->entries[pml4];

    // If the seconds directory level (Dir_Ptr) is not yet initialized initializes it
    if(!dir_ptr_pointer->entries[dir_ptr])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page)
        {
            return NULL;
        }
        // Else allocates a block of memory for a Table structure and starts it out at 0
        dir_ptr_pointer->entries[dir_ptr] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *dir_pointer = (Table*)dir_ptr_pointer->entries[dir_ptr];

    // If the third directory level (Dir) is not yet initialized initializes it
    if(!dir_pointer->entries[dir])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page)
        {
            return NULL;
        }
        // Else allocates a block of memory for a Table structure and starts it out at 0
        dir_pointer->entries[dir] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *table_pointer = (Table*)dir_pointer->entries[dir];

    // If the Table is not yet initialized initializes it
    if(!table_pointer->entries[table])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page)
        {
            return NULL;
        }
        // Else allocates a block of memory for a Table structure and starts it out at 0
        table_pointer->entries[table] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    uint8_t *page_addr = (uint8_t*)table_pointer->entries[table];

    return page_addr + offset;
}


/**
 * Writes one byte in memory.
 * Uses the decompose method to get the real address and writes the value onto the new address.
 * If the address returned is not NULL writes value on it
 * 
 * @param v_addr Virtual address given by the caller
 * @param value 1 byte data to write
 */
void write_mem(uint64_t v_addr, uint8_t value)
{
    uint8_t *physical_addr = decompose_address(v_addr, 1);
    if (physical_addr)
    {
        *physical_addr = value;
    }
}

/**
 * Reads one byte from memory.
 * Uses the decompose method to get the real address and reads its value.
 * If the address returned is NULL returns 1 to signal a Segmentation Fault
 * 
 * @param v_addr Virtual address given by the caller
 * @param result Pointer to the memory block where the result is expected to be given if it is found
 * @warning Uses 1 to signal a bad address to read and 0 to signal a success
 */
int read_mem(uint64_t v_addr, uint8_t *result)
{
    uint8_t *physical_addr = decompose_address(v_addr, 0);
    // If the physical address could not be read because of a Segmentation Fault return 1
    if (!physical_addr)
    {
        return 1;
    }

    *result = *physical_addr;
    return 0;
    
}