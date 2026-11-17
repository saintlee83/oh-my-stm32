/* Synthetic compile/link fixture. This image is never flashed or executed. */
extern unsigned long _stack_top;
extern unsigned long _bss_start;
extern unsigned long _bss_end;

volatile unsigned long heartbeat;

void Reset_Handler(void)
{
    unsigned long *cursor;
    for (cursor = &_bss_start; cursor < &_bss_end; ++cursor) {
        *cursor = 0;
    }
    for (;;) {
        ++heartbeat;
    }
}

__attribute__((section(".isr_vector"), used))
const unsigned long vectors[] = {
    (unsigned long)&_stack_top,
    (unsigned long)&Reset_Handler
};
