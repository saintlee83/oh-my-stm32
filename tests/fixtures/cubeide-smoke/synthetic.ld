/* Deliberately small synthetic regions; not a board memory configuration. */
ENTRY(Reset_Handler)
MEMORY
{
    FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 16K
    RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 4K
}
_stack_top = ORIGIN(RAM) + LENGTH(RAM);
SECTIONS
{
    .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
    .text : { *(.text*) *(.rodata*) } > FLASH
    .bss (NOLOAD) :
    {
        . = ALIGN(4);
        _bss_start = .;
        *(.bss*) *(COMMON)
        . = ALIGN(4);
        _bss_end = .;
    } > RAM
}
