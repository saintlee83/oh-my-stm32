# Firmware and peripheral changes

Build a consistent view of configuration, generated code, and runtime ownership before changing a peripheral. Work from the selected MCU and board revision.

## Reconcile CubeMX with the source

Read the IOC file alongside `Core/Inc/main.h`, GPIO initialization, peripheral MSP code, clock setup, and startup/system files. Follow the project's actual layout when those files live elsewhere.

An `ioc-diff` describes configuration keys. Verify the corresponding generated C, pin names and polarity, initial output levels, alternate functions, and state inherited from the bootloader separately. Matching IOC files do not establish identical initialization code.

Before regeneration, locate manual changes both inside and outside `USER CODE` blocks, middleware settings, and external dependencies. Limit edits to the requested behavior. When regeneration is requested, record tool/package versions and review the resulting diff for lost customizations.

## Check clock and timing calculations

Establish the MCU's clock tree, oscillator inputs, prescalers, timer clocks, and tick units from the target configuration. Trace units through timer reload/compare values, baud rates, DMA periods, and timeouts.

Use existing tests or explicit calculations to check zero, minimum, maximum, rounding, and overflow cases. Confirm clock rules and memory constraints for this MCU family before applying assumptions from another project.

## Trace buffer ownership

For each shared buffer, identify its producer, consumer, length, index handling, and reuse point. Follow access across the main loop, interrupts, DMA callbacks, and RTOS tasks. A queued operation, a transfer-complete callback, and completion of the device action may occur at different times.

Avoid introducing blocking work into an ISR or removing timeouts to mask an ownership problem. Where an RTOS is used, inspect task priorities, queue ownership, ISR APIs, stack/heap settings, and watchdog paths.

Targets with caches, multiple cores, memory protection, or security regions also need target-specific checks for DMA access and shared data. Use the project settings and MCU documentation; the CLI does not verify these conditions.

## Choose checks for the change

| Change | Relevant evidence |
|---|---|
| Pin configuration | IOC and C initialization, schematic, and board revision |
| Timing calculation | Units, clock inputs, valid range, rounding, and overflow |
| State transition | Timeout, retry, cancellation, re-entry, and ownership |
| Generated code | Regeneration diff, preserved custom code, and build result |

Reuse existing host tests or HAL fakes where available. Report compilation, electrical measurements, and device behavior separately. Connect to hardware when hardware observation is within the requested work.
