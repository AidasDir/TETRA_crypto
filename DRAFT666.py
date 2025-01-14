import argparse
import pyopencl as cl
import numpy as np
# Charger et compiler le code OpenCL
KERNEL_CODE = """
__constant ushort g_awTea1LutA[8] = { 0xDA86, 0x85E9, 0x29B5, 0x2BC6, 0x8C6B, 0x974C, 0xC671, 0x93E2 };
__constant ushort g_awTea1LutB[8] = { 0x85D6, 0x791A, 0xE985, 0xC671, 0x2B9C, 0xEC92, 0xC62B, 0x9C47 };
__constant uchar g_abTea1Sbox[256] = {
    0x9B, 0xF8, 0x3B, 0x72, 0x75, 0x62, 0x88, 0x22, 0xFF, 0xA6, 0x10, 0x4D, 0xA9, 0x97, 0xC3, 0x7B,
    0x9F, 0x78, 0xF3, 0xB6, 0xA0, 0xCC, 0x17, 0xAB, 0x4A, 0x41, 0x8D, 0x89, 0x25, 0x87, 0xD3, 0xE3,
    0xCE, 0x47, 0x35, 0x2C, 0x6D, 0xFC, 0xE7, 0x6A, 0xB8, 0xB7, 0xFA, 0x8B, 0xCD, 0x74, 0xEE, 0x11,
    0x23, 0xDE, 0x39, 0x6C, 0x1E, 0x8E, 0xED, 0x30, 0x73, 0xBE, 0xBB, 0x91, 0xCA, 0x69, 0x60, 0x49,
    0x5F, 0xB9, 0xC0, 0x06, 0x34, 0x2A, 0x63, 0x4B, 0x90, 0x28, 0xAC, 0x50, 0xE4, 0x6F, 0x36, 0xB0,
    0xA4, 0xD2, 0xD4, 0x96, 0xD5, 0xC9, 0x66, 0x45, 0xC5, 0x55, 0xDD, 0xB2, 0xA1, 0xA8, 0xBF, 0x37,
    0x32, 0x2B, 0x3E, 0xB5, 0x5C, 0x54, 0x67, 0x92, 0x56, 0x4C, 0x20, 0x6B, 0x42, 0x9D, 0xA7, 0x58,
    0x0E, 0x52, 0x68, 0x95, 0x09, 0x7F, 0x59, 0x9C, 0x65, 0xB1, 0x64, 0x5E, 0x4F, 0xBA, 0x81, 0x1C,
    0xC2, 0x0C, 0x02, 0xB4, 0x31, 0x5B, 0xFD, 0x1D, 0x0A, 0xC8, 0x19, 0x8F, 0x83, 0x8A, 0xCF, 0x33,
    0x9E, 0x3A, 0x80, 0xF2, 0xF9, 0x76, 0x26, 0x44, 0xF1, 0xE2, 0xC4, 0xF5, 0xD6, 0x51, 0x46, 0x07,
    0x14, 0x61, 0xF4, 0xC1, 0x24, 0x7A, 0x94, 0x27, 0x00, 0xFB, 0x04, 0xDF, 0x1F, 0x93, 0x71, 0x53,
    0xEA, 0xD8, 0xBD, 0x3D, 0xD0, 0x79, 0xE6, 0x7E, 0x4E, 0x9A, 0xD7, 0x98, 0x1B, 0x05, 0xAE, 0x03,
    0xC7, 0xBC, 0x86, 0xDB, 0x84, 0xE8, 0xD1, 0xF7, 0x16, 0x21, 0x6E, 0xE5, 0xCB, 0xA3, 0x1A, 0xEC,
    0xA2, 0x7D, 0x18, 0x85, 0x48, 0xDA, 0xAA, 0xF0, 0x08, 0xC6, 0x40, 0xAD, 0x57, 0x0D, 0x29, 0x82,
    0x7C, 0xE9, 0x8C, 0xFE, 0xDC, 0x0F, 0x2D, 0x3C, 0x2E, 0xF6, 0x15, 0x2F, 0xAF, 0xE1, 0xEB, 0x3F,
    0x99, 0x43, 0x13, 0x0B, 0xE0, 0xA5, 0x12, 0x77, 0x5D, 0xB3, 0x38, 0xD9, 0xEF, 0x5A, 0x01, 0x70
};

inline uchar tea1_state_word_to_newbyte(ushort wSt, __constant ushort* awLut) {
    uchar bSt0 = wSt & 0xFF;
    uchar bSt1 = (wSt >> 8) & 0xFF;
    uchar bDist;
    uchar bOut = 0;

    for (int i = 0; i < 8; i++) {
        bDist = ((bSt0 >> 7) & 1) | ((bSt0 << 1) & 2) | ((bSt1 << 1) & 12);
        if (awLut[i] & (1 << bDist)) {
            bOut |= (1 << i);
        }
        bSt0 = ((bSt0 >> 1) | (bSt0 << 7));
        bSt1 = ((bSt1 >> 1) | (bSt1 << 7));
    }

    return bOut;
}

inline uchar tea1_reorder_state_byte(uchar bStByte) {
    uchar bOut = 0;
    bOut |= ((bStByte << 6) & 0x40);
    bOut |= ((bStByte << 1) & 0x20);
    bOut |= ((bStByte << 2) & 0x08);
    bOut |= ((bStByte >> 3) & 0x14);
    bOut |= ((bStByte >> 2) & 0x01);
    bOut |= ((bStByte >> 5) & 0x02);
    bOut |= ((bStByte << 4) & 0x80);
    return bOut;
}

void tea1_inner(ulong qwIvReg, uint dwKeyReg, uint dwNumKsBytes, uchar *lpKsOut) {
    uint dwNumSkipRounds = 54;

    for (int i = 0; i < dwNumKsBytes; i++) {
        for (int j = 0; j < dwNumSkipRounds; j++) {
            // Step 1: Derive a non-linear feedback byte through sbox and feed back into key register
            uchar bSboxOut = g_abTea1Sbox[((dwKeyReg >> 24) ^ dwKeyReg) & 0xff];
            dwKeyReg = (dwKeyReg << 8) | bSboxOut;

            // Step 2: Compute 3 bytes derived from current state
            uchar bDerivByte12 = tea1_state_word_to_newbyte((qwIvReg >>  8) & 0xffff, g_awTea1LutA);
            uchar bDerivByte56 = tea1_state_word_to_newbyte((qwIvReg >> 40) & 0xffff, g_awTea1LutB);
            uchar bReordByte4  = tea1_reorder_state_byte((qwIvReg >> 32) & 0xff);

            // Step 3: Combine current state with state derived values, and xor in key derived sbox output
            uchar bNewByte = (bDerivByte56 ^ (qwIvReg >> 56) ^ bReordByte4 ^ bSboxOut) & 0xff;
            uchar bMixByte = bDerivByte12;

            // Step 4: Update lfsr: leftshift 8, feed/mix in previously generated bytes
            qwIvReg = ((qwIvReg << 8) ^ ((ulong)bMixByte << 32)) | bNewByte;
        }

        lpKsOut[i] = (qwIvReg >> 56);
        dwNumSkipRounds = 19;
    }
}
__kernel void gen_ks(__global uchar* output,
                     uint start_counter,
                     uint end_counter,
                     __global uint* stop_flag,
                     uint match,
                     ulong qwIv) {
    int gid = get_global_id(0);  // Global thread ID
    int ks_len = 54;  // Keystream length
    uint eck[4];
    uint counter = (start_counter + gid) & 0xFFFFFFFF;  // Start counter at 0

    __global uchar* ks_out = output + gid * ks_len;

    while (counter <= end_counter) {
        // Early exit if stop_flag is set
        if (*stop_flag != 0) {
            return;
        }

        // Generate encryption counter (ECK) directly from counter
        eck[0] = (uchar)(counter >> 24);
        eck[1] = (uchar)(counter >> 16);
        eck[2] = (uchar)(counter >> 8);
        eck[3] = (uchar)counter;
        uint dwKeyReg = ((uint)eck[0] << 24) | ((uint)eck[1] << 16) | ((uint)eck[2] << 8) | (uint)eck[3];

        // Generate keystream
        tea1_inner(qwIv, dwKeyReg, ks_len, ks_out);

        // Check for a specific match (first 4 bytes of keystream)
        uint ks_combined = (ks_out[0] << 24) | (ks_out[1] << 16) | (ks_out[2] << 8) | ks_out[3];
        if (ks_combined == match) {  // Match condition
            printf("Counter: %X\\n", counter);
        }
        // FOR DEBUGGING
        // if (counter % 0x1000000 == 0){printf("%X\\n",counter);}
        // Increment counter and ensure proper wrapping
        counter = (counter + get_global_size(0)) & 0xFFFFFFFF;
    }
}
"""
# Constants for the algorithm
g_awTea1LutA = [0xDA86, 0x85E9, 0x29B5, 0x2BC6, 0x8C6B, 0x974C, 0xC671, 0x93E2]
g_awTea1LutB = [0x85D6, 0x791A, 0xE985, 0xC671, 0x2B9C, 0xEC92, 0xC62B, 0x9C47]
g_abTea1Sbox = [
    0x9B, 0xF8, 0x3B, 0x72, 0x75, 0x62, 0x88, 0x22, 0xFF, 0xA6, 0x10, 0x4D, 0xA9, 0x97, 0xC3, 0x7B,
    0x9F, 0x78, 0xF3, 0xB6, 0xA0, 0xCC, 0x17, 0xAB, 0x4A, 0x41, 0x8D, 0x89, 0x25, 0x87, 0xD3, 0xE3,
    0xCE, 0x47, 0x35, 0x2C, 0x6D, 0xFC, 0xE7, 0x6A, 0xB8, 0xB7, 0xFA, 0x8B, 0xCD, 0x74, 0xEE, 0x11,
    0x23, 0xDE, 0x39, 0x6C, 0x1E, 0x8E, 0xED, 0x30, 0x73, 0xBE, 0xBB, 0x91, 0xCA, 0x69, 0x60, 0x49,
    0x5F, 0xB9, 0xC0, 0x06, 0x34, 0x2A, 0x63, 0x4B, 0x90, 0x28, 0xAC, 0x50, 0xE4, 0x6F, 0x36, 0xB0,
    0xA4, 0xD2, 0xD4, 0x96, 0xD5, 0xC9, 0x66, 0x45, 0xC5, 0x55, 0xDD, 0xB2, 0xA1, 0xA8, 0xBF, 0x37,
    0x32, 0x2B, 0x3E, 0xB5, 0x5C, 0x54, 0x67, 0x92, 0x56, 0x4C, 0x20, 0x6B, 0x42, 0x9D, 0xA7, 0x58,
    0x0E, 0x52, 0x68, 0x95, 0x09, 0x7F, 0x59, 0x9C, 0x65, 0xB1, 0x64, 0x5E, 0x4F, 0xBA, 0x81, 0x1C,
    0xC2, 0x0C, 0x02, 0xB4, 0x31, 0x5B, 0xFD, 0x1D, 0x0A, 0xC8, 0x19, 0x8F, 0x83, 0x8A, 0xCF, 0x33,
    0x9E, 0x3A, 0x80, 0xF2, 0xF9, 0x76, 0x26, 0x44, 0xF1, 0xE2, 0xC4, 0xF5, 0xD6, 0x51, 0x46, 0x07,
    0x14, 0x61, 0xF4, 0xC1, 0x24, 0x7A, 0x94, 0x27, 0x00, 0xFB, 0x04, 0xDF, 0x1F, 0x93, 0x71, 0x53,
    0xEA, 0xD8, 0xBD, 0x3D, 0xD0, 0x79, 0xE6, 0x7E, 0x4E, 0x9A, 0xD7, 0x98, 0x1B, 0x05, 0xAE, 0x03,
    0xC7, 0xBC, 0x86, 0xDB, 0x84, 0xE8, 0xD1, 0xF7, 0x16, 0x21, 0x6E, 0xE5, 0xCB, 0xA3, 0x1A, 0xEC,
    0xA2, 0x7D, 0x18, 0x85, 0x48, 0xDA, 0xAA, 0xF0, 0x08, 0xC6, 0x40, 0xAD, 0x57, 0x0D, 0x29, 0x82,
    0x7C, 0xE9, 0x8C, 0xFE, 0xDC, 0x0F, 0x2D, 0x3C, 0x2E, 0xF6, 0x15, 0x2F, 0xAF, 0xE1, 0xEB, 0x3F,
    0x99, 0x43, 0x13, 0x0B, 0xE0, 0xA5, 0x12, 0x77, 0x5D, 0xB3, 0x38, 0xD9, 0xEF, 0x5A, 0x01, 0x70
]

def tea1_expand_iv(dw_short_iv):
    """
    Expand a short IV into a full 64-bit IV as per the TEA1 algorithm.

    Args:
        dw_short_iv (int): A 32-bit integer representing the short IV.

    Returns:
        int: The expanded 64-bit IV.
    """
    dw_xorred = dw_short_iv ^ 0x96724FA1
    print(f"Debug: dwXorred (before shift) = {dw_xorred:#010x}")

    dw_xorred = ((dw_xorred << 8) & 0xFFFFFFFF) | (dw_xorred >> 24)
    print(f"Debug: dwXorred (after shift) = {dw_xorred:#010x}")

    qw_iv = (dw_short_iv << 32) | dw_xorred
    print(f"Debug: qwIv = {qw_iv:#018x}")

    expanded_iv = ((qw_iv >> 8) & 0x00FFFFFFFFFFFFFF) | ((qw_iv & 0xFF) << 56)
    print(f"Debug: Expanded IV = {expanded_iv:#018x}")

    return expanded_iv

def tea1_state_word_to_newbyte(w_st, lut):
    """
    Transform a state word into a new byte using the given LUT.
    """
    b_st0 = w_st & 0xFF
    b_st1 = (w_st >> 8) & 0xFF
    b_out = 0

    for i in range(8):
        b_dist = ((b_st0 >> 7) & 1) | ((b_st0 << 1) & 2) | ((b_st1 << 1) & 12)
        if lut[i] & (1 << b_dist):
            b_out |= (1 << i)
        b_st0 = ((b_st0 >> 1) | (b_st0 << 7)) & 0xFF
        b_st1 = ((b_st1 >> 1) | (b_st1 << 7)) & 0xFF

    return b_out

def tea1_reorder_state_byte(b_st_byte):
    """
    Reorder a state byte.
    """
    b_out = 0
    b_out |= ((b_st_byte << 6) & 0x40)
    b_out |= ((b_st_byte << 1) & 0x20)
    b_out |= ((b_st_byte << 2) & 0x08)
    b_out |= ((b_st_byte >> 3) & 0x14)
    b_out |= ((b_st_byte >> 2) & 0x01)
    b_out |= ((b_st_byte >> 5) & 0x02)
    b_out |= ((b_st_byte << 4) & 0x80)
    return b_out

def tea1_init_key_register(key):
    """
    Initialize the key register using the provided key and S-box.
    """
    dw_result = 0
    for i in range(10):
        dw_result = ((dw_result << 8) & 0xFFFFFFFF) | g_abTea1Sbox[((dw_result >> 24) ^ key[i] ^ dw_result) & 0xFF]
    return dw_result

def build_iv(frame):
    """
    Build an IV from the FrameNumbers structure.
    """
    return ((frame['tn'] - 1) |
            (frame['fn'] << 2) |
            (frame['mn'] << 7) |
            ((frame['hn'] & 0x7FFF) << 13) |
            (frame['dir'] << 28))

def prepare_key_stream(tn, fn, mn, hn, sn, direction, eck, key_length, chunk_size=0xFFFFFF):

    # Create OpenCL context
    platforms = cl.get_platforms()
    gpu_devices = [device for platform in platforms for device in platform.get_devices(device_type=cl.device_type.GPU)]
    if not gpu_devices:
        raise RuntimeError("No GPU devices found.")
    context = cl.Context(devices=gpu_devices)
    queue = cl.CommandQueue(context, properties=cl.command_queue_properties.PROFILING_ENABLE)

    # Build the OpenCL program
    try:
        program = cl.Program(context, KERNEL_CODE).build()
    except cl.RuntimeError as e:
        print("Build log:")
        for device in context.devices:
            print(program.get_build_info(device, cl.program_build_info.LOG))
        raise

    # Compute IVs in Python
    frame = {'tn': 1, 'fn': 6, 'mn': 30, 'hn': 110, 'dir': 0}
    dwIv = build_iv(frame)  # 32-bit IV
    qwIv = tea1_expand_iv(dwIv)  # 64-bit expanded IV
    print(f"Generated dwIv: {dwIv:#010x}")
    print(f"Generated qwIv: {qwIv:#018x}")

    # Check device memory limits
    device = context.devices[0]
    max_alloc_size = device.max_mem_alloc_size
    total_mem_size = device.global_mem_size
    print(f"Max Alloc Size: {max_alloc_size / (1024 ** 2):.2f} MB")
    print(f"Global Memory Size: {total_mem_size / (1024 ** 3):.2f} GB")

    # Adjust chunk size to fit within limits
    chunk_size = min(chunk_size, max_alloc_size // key_length)
    global_size = (chunk_size,)

    print(f"Adjusted Chunk Size: {chunk_size}")
    print(f"Global Work Size: {global_size}")

    # Allocate the buffer
    buffer_size = key_length * chunk_size
    if buffer_size > max_alloc_size:
        raise ValueError(f"Buffer size ({buffer_size} bytes) exceeds the maximum allowed size ({max_alloc_size} bytes).")

    output_buf = cl.Buffer(context, cl.mem_flags.WRITE_ONLY, size=buffer_size)
    stop_flag_buf = cl.Buffer(context, cl.mem_flags.READ_WRITE, size=4)

    # Initialize stop flag
    stop_flag = np.zeros(1, dtype=np.uint32)
    cl.enqueue_copy(queue, stop_flag_buf, stop_flag).wait()

    total_range = 0xFFFFFFFF
    for start in range(0, total_range, chunk_size):
        end = min(start + chunk_size - 1, total_range)

        kernel = program.gen_ks
        kernel.set_arg(0, output_buf)
        kernel.set_arg(1, np.uint32(start))
        kernel.set_arg(2, np.uint32(end))
        kernel.set_arg(3, stop_flag_buf)
        kernel.set_arg(4, np.uint32(eck))
        kernel.set_arg(5, np.uint64(qwIv))

        cl.enqueue_nd_range_kernel(queue, kernel, global_size, None).wait()

        # Retrieve and process the output
        keystream_chunk = np.empty(key_length * chunk_size, dtype=np.uint8)
        cl.enqueue_copy(queue, keystream_chunk, output_buf).wait()

        for i in range(0, len(keystream_chunk), key_length):
            ks_combined = (keystream_chunk[i] << 24) | (keystream_chunk[i + 1] << 16) | \
                          (keystream_chunk[i + 2] << 8) | keystream_chunk[i + 3]
            if ks_combined == eck:
                #print(f"Match found at counter: {start + (i // key_length):X}")
                return keystream_chunk[:i + key_length]

    print("No match found.")
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate TEA keystream.")
    parser.add_argument("tea_type", type=int, help="TEA type (1, 2, or 3)")
    parser.add_argument("hn", type=int, help="Hyperframe number (hn)")
    parser.add_argument("mn", type=int, help="Multiframe number (mn)")
    parser.add_argument("fn", type=int, help="Frame number (fn)")
    parser.add_argument("sn", type=int, help="Slot number (sn)")
    parser.add_argument("direction", type=int, help="Direction (0=downlink, 1=uplink)")
    parser.add_argument("eck", type=str, help="Encryption key (8 hex digits)")
    parser.add_argument("--key_length", type=int, default=64, help="Length of the keystream to generate (default: 64 bytes)")

    args = parser.parse_args()
    args.eck = args.eck[:8]

    try:
        eck = int(args.eck, 16)
    except ValueError:
        print("Error: `eck` must be a valid 8-character hex string.")
        return

    print(f"Generating keystream for TEA type {args.tea_type} with frame: hn={args.hn}, mn={args.mn}, fn={args.fn}, sn={args.sn}, dir={args.direction}, eck={args.eck}")

    keystream = prepare_key_stream(args.tea_type, args.hn, args.mn, args.fn, args.sn, args.direction, eck, args.key_length, chunk_size=0xFFFFFF)

if __name__ == "__main__":
    main()
