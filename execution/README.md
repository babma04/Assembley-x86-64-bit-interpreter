# Performance module

This module focuses on providing memory efficient and fast functions and structures to support the interpretation and the replication of the intended instruction.
It defines a memory handling module that should be used to read abd write data into memory, a register module that mimics the registers behavior used to map into register related instructions/ accesses, and an operations module that defines the major lookup table for the instructions to run.

## Modules

### Memory Engine

### API

|===============|============================================|====================================|
|  **Function** |              **Parameters**                |           **Results**              |
|===============|============================================|====================================|
| **table_init**|                  None                      |Table pointer to the init'ed struct;|
|===============|============================================|====================================|
|**free_table** |          Table struct pointer              |Frees up the structure from memory; |
|===============|============================================|====================================|
|               |Table struct pointer;                       |(Re)Writes bytes in the memory      |
|               |uint64_t address of the data to write;      |structure. Firstly decodes the      |
| **write_mem** |uint8_t pointer to the data to write buffer;|address and then verifies if needs  |
|               |uint8_t number of bytes to write;           |to create a new page. Then writes   |
|               |uint8_t flag to enable page creation;       |byte to byte to it;                 |
|===============|============================================|====================================|
|               |Table struct pointer;                       |Writes the data from the given      |
|               |uint64_t address of the data to write;      |address stored in memory to the     |
| **read_mem**  |uint8_t pointer to the data return buffer;  |given return data buffer.           |
|               |uint8_t number of bytes to write;           |Returns 0 on success and 1 on a miss|
|===============|============================================|====================================|

### Description
