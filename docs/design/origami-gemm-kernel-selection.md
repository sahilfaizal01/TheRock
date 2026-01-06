# Origami-Based GEMM Kernel Selection for MIOpen and Composable Kernel

## Overview

This document describes the integration of Origami-based kernel selection for GEMM operations in the PyTorch → MIOpen → Composable Kernel (CK) execution path. This integration enables intelligent, performance-optimized kernel selection for deep learning workloads running on AMD GPUs.

## Background

### Current Architecture

The ROCm software stack provides multiple paths for GEMM (General Matrix Multiply) operations:

1. **BLAS Path** (Dense GEMM): PyTorch → hipBLAS → rocBLAS → hipBLASLt → GPU
2. **DNN Path** (Convolutions/ML operations): PyTorch → hipDNN → MIOpen → Composable Kernel → GPU

Currently, these paths use different kernel selection strategies:

- **hipBLASLt**: Uses Tensile (code generation) + Origami (kernel selection) + rocRoller (performance tuning)
- **MIOpen**: Uses a plugin-based system with static routing to kernel providers (native MIOpen kernels or CK)

### The Problem

MIOpen's integration with Composable Kernel lacks sophisticated kernel selection logic. The current implementation uses simple heuristics or static routing, which may not select optimal kernels for varying problem sizes, GPU architectures, or workload characteristics.

Meanwhile, Origami (bundled within hipBLASLt) provides advanced kernel selection capabilities that are already proven effective for BLAS operations but are not accessible to the MIOpen/CK path.

## Solution: Origami-Based Kernel Selection for MIOpen

### Architecture

This integration enables Origami to select optimal CK kernels for GEMM-like operations (including convolutions that can be expressed as GEMMs) in MIOpen:

```
┌──────────┐
│ PyTorch  │
└────┬─────┘
     │
     ├────────────────────┐
     │                    │
┌────▼────┐        ┌─────▼─────┐
│ hipBLAS │        │  hipDNN   │
└────┬────┘        └─────┬─────┘
     │                   │
┌────▼────┐        ┌─────▼─────┐
│ rocBLAS │        │  MIOpen   │
└────┬────┘        └─────┬─────┘
     │                   │
┌────▼──────┐      ┌─────▼─────────────┐
│hipBLASLt  │      │ MIOpen Kernel     │
│(Origami)  │◄─────┤ Selection Layer   │
└───────────┘      │ (uses Origami)    │
                   └─────┬─────────────┘
                         │
                   ┌─────▼──────────┐
                   │  Composable    │
                   │  Kernel (CK)   │
                   └────────────────┘
```

### Key Components

1. **Origami** (in hipBLASLt)
   - Kernel selection and decision logic
   - Performance modeling and heuristics
   - Problem-size and architecture-aware selection

2. **rocRoller** (optional)
   - Runtime performance profiling
   - Dynamic kernel selection based on actual measurements
   - Complements Origami's static heuristics

3. **MIOpen Kernel Selection Layer** (to be implemented in rocm-libraries/projects/miopen)
   - Interface between MIOpen and Origami
   - Translates MIOpen problem descriptors to Origami's format
   - Routes selected kernels to appropriate CK implementations

4. **Composable Kernel**
   - Provides high-performance kernel implementations
   - Receives kernel selection decisions from Origami

### CMake Integration

The integration is controlled by the CMake option `THEROCK_MIOPEN_USE_ORIGAMI_SELECTION`:

```cmake
# CMakeLists.txt
cmake_dependent_option(THEROCK_MIOPEN_USE_ORIGAMI_SELECTION
  "Enables Origami-based GEMM kernel selection for MIOpen CK backend" ON
  "THEROCK_ENABLE_MIOPEN;THEROCK_ENABLE_BLAS;THEROCK_MIOPEN_USE_COMPOSABLE_KERNEL" OFF)
```

**Dependencies:**
- Requires MIOpen to be enabled (`THEROCK_ENABLE_MIOPEN`)
- Requires BLAS stack to be enabled (`THEROCK_ENABLE_BLAS`) for access to hipBLASLt/Origami
- Requires Composable Kernel integration (`THEROCK_MIOPEN_USE_COMPOSABLE_KERNEL`)
- Non-Windows platforms only

**Build Configuration:**

When enabled:
1. hipBLASLt is added as a build dependency for MIOpen (provides Origami access)
2. rocRoller is added as a runtime dependency (if available) for performance profiling
3. `MIOPEN_USE_ORIGAMI_SELECTION` flag is passed to MIOpen's build system

## Implementation Details

### MIOpen Build Configuration

In `ml-libs/CMakeLists.txt`:

```cmake
# Add hipBLASLt and rocRoller dependencies when Origami selection is enabled
set(optional_miopen_origami_deps)
if(THEROCK_MIOPEN_USE_ORIGAMI_SELECTION)
  list(APPEND optional_miopen_build_deps hipBLASLt)
  if(TARGET rocRoller)
    list(APPEND optional_miopen_origami_deps rocRoller)
  endif()
endif()

# Pass flag to MIOpen
CMAKE_ARGS
  "-DMIOPEN_USE_ORIGAMI_SELECTION=${THEROCK_MIOPEN_USE_ORIGAMI_SELECTION}"
  ...
```

### Expected MIOpen Changes (in rocm-libraries)

The actual implementation within MIOpen (in the rocm-libraries repository) should include:

1. **Kernel Selection Interface** (`miopen/include/miopen/kernel_selector.hpp`):
   ```cpp
   namespace miopen {

   class OrigamiKernelSelector {
   public:
       // Select optimal CK kernel for given problem
       CKKernelDescriptor SelectKernel(
           const ConvolutionDescriptor& conv_desc,
           const TensorDescriptor& input_desc,
           const TensorDescriptor& weight_desc,
           const TensorDescriptor& output_desc,
           const std::string& arch_name);

   private:
       // Interface to hipBLASLt's Origami
       std::shared_ptr<OrigamiInterface> origami_;
   };

   } // namespace miopen
   ```

2. **Integration with CK Backend**:
   - Modify MIOpen's CK kernel provider to use OrigamiKernelSelector
   - Map convolution/GEMM problem parameters to Origami's problem format
   - Use Origami's selection decision to instantiate appropriate CK kernels

3. **Fallback Mechanism**:
   - If Origami selection fails or is unavailable, fall back to existing heuristics
   - Ensure backward compatibility when `MIOPEN_USE_ORIGAMI_SELECTION=OFF`

### Kernel Selection Flow

```
1. PyTorch invokes GEMM/Convolution operation
   ↓
2. hipDNN routes to MIOpen
   ↓
3. MIOpen extracts problem parameters:
   - Matrix/tensor dimensions
   - Data types
   - GPU architecture (gfx908, gfx90a, gfx942, gfx950)
   ↓
4. MIOpen queries OrigamiKernelSelector
   ↓
5. Origami analyzes:
   - Problem size and characteristics
   - GPU microarchitecture capabilities
   - Performance models and heuristics
   - rocRoller profiling data (if available)
   ↓
6. Origami selects optimal CK kernel variant
   ↓
7. MIOpen instantiates and invokes selected CK kernel
   ↓
8. Kernel executes on GPU
```

## Benefits

1. **Improved Performance**: Origami's sophisticated selection logic ensures optimal kernel choice for varying workloads
2. **Unified Selection Strategy**: Consistent kernel selection approach across BLAS and DNN paths
3. **Architecture Awareness**: Leverages Origami's understanding of GPU microarchitecture details
4. **Dynamic Adaptation**: With rocRoller integration, can adapt to actual runtime performance
5. **Code Reuse**: Leverages existing, proven Origami infrastructure rather than duplicating selection logic

## GPU Architecture Support

Origami-based kernel selection for MIOpen is supported on the same GPU architectures as Composable Kernel:

- **gfx908** (MI100)
- **gfx90a** (MI200 series)
- **gfx942** (MI300A)
- **gfx950** (MI300X and future architectures)

The integration automatically disables if unsupported architectures are targeted.

## Future Work

1. **Origami Extraction** (per RFC0003):
   - Move Origami from bundled hipBLASLt component to shared "codegen" category
   - Create standalone Origami library that both hipBLASLt and MIOpen can depend on
   - Enables independent versioning and development

2. **Extended Kernel Coverage**:
   - Expand beyond GEMM-like operations to other MIOpen kernels
   - Support for normalization, activation, and pooling operations

3. **Runtime Learning**:
   - Integrate with rocRoller's profiling to continuously improve selection
   - Build per-system performance databases

4. **MLIR Integration**:
   - Coordinate with MIOpen's planned MLIR support
   - Use Origami for kernel variant selection in MLIR-generated kernels

5. **hipDNN Plugin Architecture**:
   - Extend to support Fusilli/IREE kernel providers (per RFC0004)
   - Enable Origami to select across multiple kernel provider backends

## Testing and Validation

### Unit Tests
- Test kernel selection for various problem sizes
- Verify correct CK kernel instantiation
- Validate fallback mechanisms

### Integration Tests
- End-to-end PyTorch → MIOpen → CK execution
- Correctness validation against reference implementations
- Performance regression testing

### Performance Benchmarks
- Compare Origami-selected vs. default heuristics
- Measure overhead of selection logic
- Validate performance improvements across representative workloads

## Build and Configuration

### Building with Origami Selection

```bash
cmake -DTHEROCK_MIOPEN_USE_ORIGAMI_SELECTION=ON \
      -DTHEROCK_ENABLE_MIOPEN=ON \
      -DTHEROCK_ENABLE_BLAS=ON \
      -DTHEROCK_MIOPEN_USE_COMPOSABLE_KERNEL=ON \
      ...
```

### Disabling Origami Selection

```bash
cmake -DTHEROCK_MIOPEN_USE_ORIGAMI_SELECTION=OFF ...
```

Or build without BLAS support (Origami won't be available).

### Runtime Environment

No special runtime configuration required. The selected kernels are determined at operation invocation time based on problem parameters.

## References

- [RFC0003: Build Tree Normalization](../rfcs/RFC0003-Build-Tree-Normalization.md) - Proposes moving Origami to codegen category
- [RFC0001: BLAS Stack Build Improvements](../rfcs/RFC0001-BLAS-Stack-Build-Improvements.md) - Origami migration planning
- [RFC0004: Fusilli IREE Kernel Provider](../rfcs/RFC0004-Fusilli-IREE-Kernel-Provider-hipDNN.md) - Future hipDNN plugin architecture
- [RFC0005: hipDNN Project Integration](../rfcs/RFC0005-hipDNN-Project-Integration.md) - hipDNN and MIOpen plugin system

## Appendix: Implementation Checklist

### TheRock Repository (Completed)
- [x] Add `THEROCK_MIOPEN_USE_ORIGAMI_SELECTION` CMake option
- [x] Configure MIOpen build dependencies (hipBLASLt, rocRoller)
- [x] Pass `MIOPEN_USE_ORIGAMI_SELECTION` flag to MIOpen build
- [x] Document architecture and design

### rocm-libraries/MIOpen (To be implemented)
- [ ] Create `OrigamiKernelSelector` interface
- [ ] Implement Origami integration layer
- [ ] Modify CK backend to use Origami selection
- [ ] Add CMake handling for `MIOPEN_USE_ORIGAMI_SELECTION` flag
- [ ] Implement fallback mechanisms
- [ ] Add unit tests for kernel selection
- [ ] Add integration tests for end-to-end execution
- [ ] Update MIOpen documentation

### rocm-libraries/hipBLASLt (Future)
- [ ] Extract Origami to shared library (per RFC0003)
- [ ] Create public API for external consumers
- [ ] Define stable interface for kernel selection queries

## Conclusion

Origami-based GEMM kernel selection for MIOpen provides a sophisticated, performance-optimized approach to kernel dispatch in the PyTorch → MIOpen → Composable Kernel execution path. By leveraging existing, proven infrastructure from the BLAS stack, this integration improves performance while maintaining code quality and reducing duplication.

The implementation is designed for incremental adoption, with clear fallback mechanisms and build-time configurability, ensuring compatibility with existing workflows while enabling advanced optimization for production deployments.
