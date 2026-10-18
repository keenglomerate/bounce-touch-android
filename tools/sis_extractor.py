import struct
import zlib
import os
import sys

class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def tell(self):
        return self.pos

    def seek(self, pos):
        self.pos = pos

    def skip(self, n):
        self.pos += n

    def read(self, n):
        res = self.data[self.pos:self.pos+n]
        self.pos += len(res)
        return res

    def align(self):
        rem = self.pos % 4
        if rem != 0:
            self.pos += (4 - rem)

    def read_u8(self):
        return struct.unpack("<B", self.read(1))[0]

    def read_u16(self):
        return struct.unpack("<H", self.read(2))[0]

    def read_u32(self):
        return struct.unpack("<I", self.read(4))[0]

    def read_u64(self):
        return struct.unpack("<Q", self.read(8))[0]

    def peek_u32(self):
        if self.pos + 4 <= len(self.data):
            return struct.unpack("<I", self.data[self.pos:self.pos+4])[0]
        return None

    def read_field_header(self, has_type=True):
        ftype = self.read_u32() if has_type else None
        len_low = self.read_u32()
        if (len_low >> 31) == 1:
            len_high = self.read_u32()
            length = (len_low & 0x7FFFFFFF) | (len_high << 31)
        else:
            length = len_low
        return ftype, length

def parse_compressed(r, no_extract=False):
    ftype, length = r.read_field_header(True)
    algo = r.read_u32() # 0 = none, 1 = deflated
    uncompressed_size = r.read_u64()
    compressed_size = length - 12
    compressed_bytes = r.read(compressed_size)
    r.align()
    if algo == 1:
        uncompressed = zlib.decompress(compressed_bytes)
        assert len(uncompressed) == uncompressed_size, f"Decompressed size mismatch: {len(uncompressed)} vs {uncompressed_size}"
    else:
        uncompressed = compressed_bytes
    return uncompressed

def parse_string(r, has_type=True):
    ftype, length = r.read_field_header(has_type)
    raw = r.read(length)
    r.align()
    return raw.decode("utf-16le", "ignore")

def parse_array(r, elem_parser, has_type=True):
    ftype, length = r.read_field_header(has_type)
    elem_type = r.read_u32()
    start = r.tell()
    total_payload = length - 4
    elems = []
    while r.tell() - start < total_payload:
        elem = elem_parser(r, elem_type)
        elems.append(elem)
        r.align()
    r.align()
    return elems

def parse_blob(r, has_type=True):
    ftype, length = r.read_field_header(has_type)
    data = r.read(length)
    r.align()
    return data

def parse_file_des(r, has_type=True):
    ftype, length = r.read_field_header(has_type)
    target = parse_string(r, True)
    mime = parse_string(r, True)
    # Check for caps
    if r.peek_u32() == 41: # SISCapabilities
        caps = parse_blob(r, True)
    else:
        caps = None
    # SISHash:
    hash_type, hash_len = r.read_field_header(True)
    hash_algo = r.read_u32()
    hash_data = parse_blob(r, True)
    r.align()

    op = r.read_u32()
    op_op = r.read_u32()
    len_f = r.read_u64()
    uncompressed_len = r.read_u64()
    idx = r.read_u32()
    r.align()
    return {
        "target": target,
        "mime": mime,
        "op": op,
        "len": len_f,
        "uncompressed_len": uncompressed_len,
        "idx": idx
    }

def unpack_sis(filepath, out_dir):
    with open(filepath, "rb") as f:
        data = f.read()

    r = Reader(data)
    uid1, uid2, uid3, checksum = struct.unpack("<IIII", r.read(16))
    print(f"UID: {hex(uid1)} {hex(uid2)} {hex(uid3)} Checksum: {hex(checksum)}")

    # Contents
    c_type, c_len = r.read_field_header(True)
    print(f"Contents field: type={c_type}, len={c_len}")

    if r.peek_u32() == 34: # SISControllerChecksum
        r.read_field_header(True)
        r.read_u16()
        r.align()

    if r.peek_u32() == 35: # SISDataChecksum
        r.read_field_header(True)
        r.read_u16()
        r.align()

    controller_bytes = parse_compressed(r)
    print(f"Decompressed controller size: {len(controller_bytes)}")

    # In controller: parse controller fields
    cr = Reader(controller_bytes)
    ctrl_type, ctrl_len = cr.read_field_header(True)
    print(f"Controller type: {ctrl_type}, len: {ctrl_len}")

    # Info:
    info_type, info_len = cr.read_field_header(True)
    # uid:
    cr.read_field_header(True)
    app_uid = cr.read_u32()
    cr.align()
    vendor = parse_string(cr, True)
    # names
    names = parse_array(cr, lambda rr, et: parse_string(rr, False), True)
    # vendor names
    vendor_names = parse_array(cr, lambda rr, et: parse_string(rr, False), True)
    # version: major, minor, build
    cr.read_field_header(True)
    v_maj, v_min, v_bld = cr.read_u32(), cr.read_u32(), cr.read_u32()
    cr.align()
    # date_time:
    cr.read_field_header(True)
    # date:
    cr.read_field_header(True)
    year, month, day = cr.read_u16(), cr.read_u8(), cr.read_u8()
    cr.align()
    # time:
    cr.read_field_header(True)
    hr, mn, sc = cr.read_u8(), cr.read_u8(), cr.read_u8()
    cr.align()
    install_type = cr.read_u8()
    install_flag = cr.read_u8()
    cr.align()

    print(f"App: {names}, Vendor: {vendor}, UID: 0x{app_uid:08x}, Version: {v_maj}.{v_min}.{v_bld}")

    # Next options:
    opt_type, opt_len = cr.read_field_header(True)
    cr.skip(opt_len)
    cr.align()

    # Next langs:
    lang_type, lang_len = cr.read_field_header(True)
    cr.skip(lang_len)
    cr.align()

    # Next prerequisites:
    pre_type, pre_len = cr.read_field_header(True)
    cr.skip(pre_len)
    cr.align()

    # Next properties:
    prop_type, prop_len = cr.read_field_header(True)
    cr.skip(prop_len)
    cr.align()

    # Logo if present:
    if cr.peek_u32() == 23:
        logo_type, logo_len = cr.read_field_header(True)
        cr.skip(logo_len)
        cr.align()

    # InstallBlock (28):
    ib_type, ib_len = cr.read_field_header(True)
    print(f"InstallBlock type: {ib_type}, len: {ib_len}")

    # Files array:
    files = parse_array(cr, lambda rr, et: parse_file_des(rr, False), True)
    print(f"Found {len(files)} files in manifest:")
    for f in files:
        print(f"  [{f['idx']}] {f['target']} (size={f['uncompressed_len']})")

    # Now back in root reader `r`, parse data:
    data_type, data_len = r.read_field_header(True)
    print(f"Data field: type={data_type}, len={data_len}")

    # Data units array:
    # Array of SISDataUnit
    data_arr_type, data_arr_len = r.read_field_header(True)
    elem_t = r.read_u32() # SISDataUnit (31)
    print(f"Data units array elem_type: {elem_t}")

    # For each data unit:
    # A SISDataUnit has an array of SISFileData
    data_units = []
    # parse the data unit
    du_type, du_len = r.read_field_header(False)
    # inside du, array of file_data
    fda_type, fda_len = r.read_field_header(True)
    fda_elem_t = r.read_u32() # SISFileData (32)
    fda_start = r.tell()
    fda_payload = fda_len - 4

    file_payloads = []
    while r.tell() - fda_start < fda_payload:
        # SISFileData:
        fd_type, fd_len = r.read_field_header(False) # element without type
        # Inside SISFileData is SISCompressed (3):
        decomp = parse_compressed(r, False)
        file_payloads.append(decomp)
        r.align()

    print(f"Extracted {len(file_payloads)} file payloads!")

    # Write files out:
    for idx, fdesc in enumerate(files):
        target = fdesc["target"]
        clean_target = target.replace("!:", "drive").replace("c:", "drive_c").replace("C:", "drive_c").replace("e:", "drive_e").replace("E:", "drive_e")
        clean_target = clean_target.replace("\\", "/")
        if clean_target.startswith("/"):
            clean_target = clean_target[1:]
        out_path = os.path.join(out_dir, clean_target)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if not clean_target or clean_target.endswith("/"):
            os.makedirs(out_path, exist_ok=True)
            continue
        if os.path.isdir(out_path):
            continue
        payload = file_payloads[fdesc["idx"]]
        with open(out_path, "wb") as out_f:
            out_f.write(payload)
        print(f"Extracted: {clean_target} ({len(payload)} bytes)")

if __name__ == "__main__":
    sis_path = "/home/keen/.gemini/antigravity-cli/brain/b8e50268-563d-463e-b9ff-ea77614c12cb/scratch/extracted/Bounce Touch (S60 5th)(Misc).sis"
    out_dir = "/home/keen/.gemini/antigravity-cli/brain/b8e50268-563d-463e-b9ff-ea77614c12cb/scratch/unpacked_game"
    os.makedirs(out_dir, exist_ok=True)
    unpack_sis(sis_path, out_dir)
