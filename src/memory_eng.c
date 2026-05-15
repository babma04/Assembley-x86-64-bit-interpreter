#include "../include/memory_eng.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// --- Constants ---
#define PAGE_SIZE 4096  // 4kb per page
#define MAX_PAGES 512 // 512 * 8 bytes per entry = 4kb tables

// --- Structures ---
struct Table {
    void *entries[MAX_PAGES];
};


/**
 * @brief Initializes the pointer to the first level of the paging structure (PML4)
 * * Allocates memory for a Table structure and initializes it to zero.
 * * Returns a pointer to the initialized Table structure.
 * @return Pointer to the initialized Table structure, or NULL if memory allocation fails
 * @warning This function should be called before any memory access operations to ensure that the paging structure is properly initialized.
 * * If memory allocation fails, the function will return NULL, and subsequent memory access operations will not be possible until the issue is resolved.
 */
Table* table_init()
{
    Table* table = (Table*)calloc(1, sizeof(Table));
    if (!table) {
        printf ("Failed memory allocation for table initializer!\n Major error detected, exiting...\n");
        return NULL;
    }
    return table;
}


/**
 * @brief Frees the memory allocated for the paging structure.
 * * Recursively frees all allocated pages and tables in the paging structure, starting from the given Table pointer.
 * * After freeing all allocated memory, the function also frees the Table structure itself.
 * @param table Pointer to the Table structure representing the root of the paging structure to be freed
 * @warning This function should be called when the paging structure is no longer needed to prevent memory leaks. 
 * * If the provided pointer is NULL, the function will simply return without performing any operations.
 */
void free_table(Table* table)
{
    if (!table) return;

    // Free all allocated pages in the table
    for (int i = 0; i < MAX_PAGES; i++) {
        if (table->entries[i]) {
            free_table((Table*)table->entries[i]); // Recursively free sub-tables
        }
    }
    // Free the table itself
    free(table);
}

/**
 * @brief Main MMU funion. 
 * * Should initialize the Table structure if it's not yet created.
 * * Used to handle reads and writes as well as manage page creation if needed.
 * 
 * @param v_addr Virtual address given by the caller
 * @param create_page Flags for the operation type (0 - for read; 1 - for write)
 * @return Pointer to the physical byte, or NULL if unmapped and create_page is 0
 * @note create_page param affects directly Table structures creation permission. 
 */
uint8_t *decompose_address (Table *CR3, uint64_t v_addr, uint8_t create_page)
{
    // If the page_dir_root is not yet initialized initialize it
    if (!CR3)
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if (!create_page) return NULL;
        // Else allocates a block of memory for a Table structure and starts it out at 0
        CR3 = (Table*)calloc(1, sizeof(Table));
    }

    // Table index and offset extraction:
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
        if(!create_page) return NULL;
        // Else allocates a block of memory for a Table structure and starts it out at 0
        CR3->entries[pml4] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *dir_ptr_pointer = (Table*)CR3->entries[pml4];

    // If the seconds directory level (Dir_Ptr) is not yet initialized initializes it
    if(!dir_ptr_pointer->entries[dir_ptr])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page) return NULL;
        // Else allocates a block of memory for a Table structure and starts it out at 0
        dir_ptr_pointer->entries[dir_ptr] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *dir_pointer = (Table*)dir_ptr_pointer->entries[dir_ptr];

    // If the third directory level (Dir) is not yet initialized initializes it
    if(!dir_pointer->entries[dir])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page) return NULL;
        // Else allocates a block of memory for a Table structure and starts it out at 0
        dir_pointer->entries[dir] = calloc(1, sizeof(Table));
    }
    // Else takes its pointer
    Table *table_pointer = (Table*)dir_pointer->entries[dir];

    // If the Table is not yet initialized initializes it
    if(!table_pointer->entries[table])
    {
        // If create_pages is 0 then i can't read any page in this stage and should return NULL
        if(!create_page) return NULL;
        // Else allocates a block of memory for a Table structure and starts it out at 0
        table_pointer->entries[table] = calloc(1, PAGE_SIZE);
    }
    // Else takes its pointer
    uint8_t *page_addr = (uint8_t*)table_pointer->entries[table];

    return page_addr + offset;
}


/**
 * @brief Writes bytes in memory.
 * * Uses the decompose method to get the real address and writes the value onto the new address.
 * * If the address returned is not NULL writes value on it, else returns without writing.
 * * Handles page crossing by checking if the write stays within the 4KB boundary.
 * * If the amount of bytes to write is grater than one uses the write_block function to handle the write operation.
 * 
 * @param v_addr Virtual address given by the caller
 * @param data Pointer to the data to write
 * @param size Size of the data to write in bytes (1,2,4,8)
 * @param create_page Flag to indicate if pages should be created if they don't exist
 * @return 0 on success, 1 if the write operation encounters an unmapped address (Segmentation Fault)
 * @warning This function assumes that the data block does not exceed the maximum size of the virtual address space.
 * @note The create_page flag affects directly the permission to create new pages in the memory.
 * If set to 0, the function will not create new pages and will return without writing if the target page does not exist. 
 * If set to 1, the function will create new pages as needed to accommodate the write operation.
 */
int write_mem (Table* table, uint64_t v_addr, uint8_t *data, uint8_t size, uint8_t create_page)
{
    if (size == 1)
    {
        uint8_t *physical_addr = decompose_address(table, v_addr, create_page);
        if (!physical_addr) return 1;
        *physical_addr = *data;
    }
    else write_block(table, v_addr, data, size, create_page);
    return 0;
}

/**
 * @brief Writes a block of data to virtual memory.
 * * Handles page crossing by checking if the write stays within the 4KB boundary.
 * 
 * @param v_addr Virtual address where the block should be written
 * @param data Pointer to the block of data to be written
 * @param size Size of the data block in bytes
 * @param create_page Flag to indicate if pages should be created if they don't exist
 * @return 0 on success, 1 if the write operation encounters an unmapped address (Segmentation Fault)
 * @warning This function assumes that the data block does not exceed the maximum size of the virtual address space.
 * @note The create_page flag affects directly the permission to create new pages in the memory.
 * If set to 0, the function will not create new pages and will return without writing if the target page does not exist. 
 * If set to 1, the function will create new pages as needed to accommodate the write operation.
 */
int write_block (Table* table, uint64_t v_addr, uint8_t *data, uint8_t size, uint8_t create_page)
{
    size_t written = 0;
    while (written < size)
    {
        uint64_t current_addr = v_addr + written;
        uint8_t *physical_addr = decompose_address(table, current_addr, create_page);
        // If the physical address could not be read because of a Segmentation Fault return without writing
        if (!physical_addr) return 1;

        uint64_t offset = current_addr & 0xFFF; // Offset within the page
        size_t space_in_page = PAGE_SIZE - offset; // Space left in the current page
        size_t to_write = (size - written < space_in_page) ? (size - written) : space_in_page; // Amount to write in the current page

        memcpy(physical_addr, data + written, to_write);
        written += to_write;
    }
    return 0;
}

/**
 * @brief Reads bytes from virtual memory.
 * * Uses the decompose method to get the real address and reads its value.
 * * If the address returned is NULL returns 1 to signal a Segmentation Fault.
 * * Handles page crossing by checking if the read stays within the 4KB boundary.
 * * If the amount of bytes to read is grater than one uses the read_block function to handle the read operation.
 * 
 * @param v_addr Virtual address given by the caller
 * @param buffer Pointer to the memory block where the result is expected to be given if it is found
 * @param size Size of the data block to be read in bytes
 * @warning Uses 1 to signal a bad address to read and 0 to signal a success
 * @warning This function assumes that the data block does not exceed the maximum size of the virtual address space.
 */
int read_mem (Table* table, uint64_t v_addr, uint8_t *buffer, uint8_t size)
{
    if (size == 1)
    {
        uint8_t *physical_addr = decompose_address(table, v_addr, 0);
        // If the physical address could not be read because of a Segmentation Fault return 1
        if (!physical_addr) return 1;
        *buffer = *physical_addr;
        return 0;
    }
        return read_block(table, v_addr, buffer, size);    
}

/**
 * @brief Reads a block of data from virtual memory.
 * * Handles page crossing by checking if the read stays within the 4KB boundary.
 * 
 * @param v_addr Virtual address where the block should be read from
 * @param buffer Pointer to the buffer where the read data should be stored
 * @param size Size of the data block to be read in bytes
 * @return 0 on success, 1 if any part of the read operation encounters an unmapped address (Segmentation Fault)
 */
int read_block (Table* table, uint64_t v_addr, uint8_t *buffer, uint8_t size)
{
    size_t read = 0;
    while (read < size)
    {
        uint64_t current_addr = v_addr + read;
        uint8_t *physical_addr = decompose_address(table, current_addr, 0);

        // If the physical address could not be read because of a Segmentation Fault return 1
        if (!physical_addr) return 1;

        uint64_t offset = current_addr & 0xFFF; // Offset within the page
        size_t space_in_page = PAGE_SIZE - offset; // Space left in the current page
        size_t to_read = (size - read < space_in_page) ? (size - read) : space_in_page; // Amount to read in the current page
        memcpy(buffer + read, physical_addr + offset, to_read);
        read += to_read;
    }
    return 0;
}
