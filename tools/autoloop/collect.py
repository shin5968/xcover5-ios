"""Save a frozen XCover5 USB snapshot before acknowledging download reset.

Standard-library Windows WinUSB backend. No firmware flashing or driver changes.
"""
from __future__ import annotations
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import uuid
import zlib

GUID = '{C2CE5A15-419F-4B2B-B547-25F3CD8F78A1}'
META = struct.Struct('<QQ6I')
MAGIC = 0x31474F4C4358
CAP = 1024 * 1024


class WinUSB:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('The physical USB backend requires Windows')
        self.setup = C.WinDLL('setupapi', use_last_error=True)
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        self.usb = C.WinDLL('winusb', use_last_error=True)
        self.handle = self.interface = None
        self.kernel.CreateFileW.argtypes = [W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
        self.kernel.CreateFileW.restype = W.HANDLE
        self.kernel.CloseHandle.argtypes = [W.HANDLE]
        self.setup.SetupDiGetClassDevsW.argtypes = [C.c_void_p,W.LPCWSTR,W.HWND,W.DWORD]
        self.setup.SetupDiGetClassDevsW.restype = W.HANDLE
        self.setup.SetupDiEnumDeviceInterfaces.argtypes = [W.HANDLE,C.c_void_p,C.c_void_p,W.DWORD,C.c_void_p]
        self.setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [W.HANDLE,C.c_void_p,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p]
        self.setup.SetupDiDestroyDeviceInfoList.argtypes = [W.HANDLE]
        self.usb.WinUsb_Initialize.argtypes = [W.HANDLE,C.POINTER(W.HANDLE)]
        self.usb.WinUsb_Free.argtypes = [W.HANDLE]
        self.usb.WinUsb_SetPipePolicy.argtypes = [W.HANDLE,C.c_ubyte,W.ULONG,W.ULONG,C.c_void_p]
        class SetupPacket(C.Structure):
            _pack_ = 1
            _fields_ = [('RequestType',C.c_ubyte),('Request',C.c_ubyte),('Value',C.c_ushort),('Index',C.c_ushort),('Length',C.c_ushort)]
        self.packet = SetupPacket
        self.usb.WinUsb_ControlTransfer.argtypes = [W.HANDLE,SetupPacket,C.c_void_p,W.ULONG,C.POINTER(W.ULONG),C.c_void_p]

    def paths(self,interface_guid=GUID):
        guid = C.create_string_buffer(uuid.UUID(interface_guid).bytes_le)
        info = self.setup.SetupDiGetClassDevsW(guid,None,None,0x12)
        if info == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())
        class InterfaceData(C.Structure):
            _fields_ = [('size',W.DWORD),('guid',C.c_ubyte*16),('flags',W.DWORD),('reserved',C.c_void_p)]
        result = []
        try:
            index = 0
            while True:
                item = InterfaceData(); item.size = C.sizeof(item)
                if not self.setup.SetupDiEnumDeviceInterfaces(info,None,guid,index,C.byref(item)):
                    error = C.get_last_error()
                    if error == 259: break
                    raise C.WinError(error)
                size = W.DWORD()
                self.setup.SetupDiGetDeviceInterfaceDetailW(info,C.byref(item),None,0,C.byref(size),None)
                if C.get_last_error() != 122: raise C.WinError(C.get_last_error())
                buf = C.create_string_buffer(size.value)
                W.DWORD.from_buffer(buf).value = 8 if C.sizeof(C.c_void_p)==8 else 6
                if not self.setup.SetupDiGetDeviceInterfaceDetailW(info,C.byref(item),buf,size,None,None):
                    raise C.WinError(C.get_last_error())
                result.append(C.wstring_at(C.addressof(buf)+4))
                index += 1
        finally:
            self.setup.SetupDiDestroyDeviceInfoList(info)
        return result

    def connect(self):
        paths = self.paths()
        if not paths: return False
        if len(paths) != 1: raise RuntimeError('Multiple XCover5 test interfaces; refusing ambiguous target')
        self.handle = self.kernel.CreateFileW(paths[0],0xc0000000,3,None,3,0x40000000,None)
        if self.handle == C.c_void_p(-1).value:
            self.handle = None; raise C.WinError(C.get_last_error())
        interface = W.HANDLE()
        if not self.usb.WinUsb_Initialize(self.handle,C.byref(interface)):
            error=C.get_last_error(); self.close(); raise C.WinError(error)
        self.interface=interface
        timeout=W.ULONG(3000)
        if not self.usb.WinUsb_SetPipePolicy(self.interface,0,3,C.sizeof(timeout),C.byref(timeout)):
            error=C.get_last_error();self.close();raise C.WinError(error)
        return True

    def transfer(self,request,offset=0,data=None,length=0):
        incoming=data is None
        if not 0 <= offset <= 0xffffffff: raise ValueError('Offset outside wire ABI')
        payload=bytes(data) if not incoming else bytes(length)
        buf=C.create_string_buffer(payload,max(1,len(payload)))
        packet=self.packet(0xc0 if incoming else 0x40,request,offset&65535,offset>>16,len(payload))
        got=W.ULONG()
        if not self.usb.WinUsb_ControlTransfer(self.interface,packet,buf,len(payload),C.byref(got),None):
            raise C.WinError(C.get_last_error())
        if not incoming and got.value != len(payload): raise IOError('Short USB OUT transfer')
        return buf.raw[:got.value]

    def close(self):
        if self.interface: self.usb.WinUsb_Free(self.interface);self.interface=None
        if self.handle: self.kernel.CloseHandle(self.handle);self.handle=None


def parse_meta(raw):
    if len(raw)!=META.size: raise ValueError('Invalid metadata length')
    magic,run,version,ready,size,crc,dropped,status=META.unpack(raw)
    if magic!=MAGIC or version!=1 or ready not in (0,1) or size>CAP:
        raise ValueError('Invalid snapshot metadata')
    if ready and not run: raise ValueError('Frozen snapshot has no run identity')
    return dict(run=run,ready=ready,size=size,crc=crc,dropped=dropped,wait_status=status)


def durable(path,body):
    # Never overwrite a prior capture. Publish only after fsync.
    with path.open('xb') as f:
        f.write(body);f.flush();os.fsync(f.fileno())


def collect(link,out:Path,reboot=False,expected_firmware=None):
    raw=link.transfer(0x40,length=META.size);meta=parse_meta(raw)
    if not meta['ready']: return None
    blob=bytearray()
    while len(blob)<meta['size']:
        count=min(256,meta['size']-len(blob))
        chunk=link.transfer(0x41,offset=len(blob),length=count)
        if len(chunk)!=count: raise IOError('Short log transfer; reset is prohibited')
        blob.extend(chunk)
    if zlib.crc32(blob)!=meta['crc']: raise ValueError('Log CRC mismatch; reset is prohibited')
    if link.transfer(0x40,length=META.size)!=raw: raise ValueError('Snapshot identity changed during transfer')
    out.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime('%Y%m%d-%H%M%S')+'-'+format(meta['run'],'016x')
    folder=out/stamp;folder.mkdir(exist_ok=False)
    durable(folder/'console.bin',blob)
    durable(folder/'console.txt',bytes(blob).decode('utf-8',errors='replace').encode('utf-8'))
    meta.update(sha256=hashlib.sha256(blob).hexdigest(),usb_protocol=1,
                artifact_kind='real-device-log',saved_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                expected_firmware=expected_firmware,
                interpretation='wait_status is the real test exit, not an automatic PASS; expected firmware is a PC record, not device attestation')
    durable(folder/'receipt.json',(json.dumps(meta,indent=2)+'\n').encode())
    # Read back the exact durable binary before ACK, including empty snapshots.
    if (folder/'console.bin').read_bytes()!=blob: raise IOError('Disk readback mismatch')
    if meta['dropped']:
        durable(folder/'PARTIAL',b'Capture overflow. Retained bytes saved; no ACK or reboot permitted.\n')
        return folder
    link.transfer(0x42,data=raw)
    durable(folder/'acknowledged.json',b'{"pc_saved_and_acknowledged": true}\n')
    if reboot:
        link.transfer(0x43,data=b'')
        durable(folder/'download-requested.json',b'{"request_sent":true,"download_enumeration":"PENDING"}\n')
    # Consumers use the per-run receipt. Never infer Odin readiness from this file.
    durable(folder/'COMPLETE',b'Log saved and acknowledged.\n')
    return folder


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[3]/'artifacts'/'autoloop-runs')
    p.add_argument('--reboot-download',action='store_true',help='Request download reset ONLY after a durable verified snapshot')
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--inventory',action='store_true',help='Read matching WinUSB interfaces, without control transfers')
    p.add_argument('--firmware-manifest',type=Path,help='Record the expected flashed build; not device attestation')
    args=p.parse_args();link=WinUSB()
    if args.inventory: print(json.dumps(link.paths()));return
    expected=json.loads(args.firmware_manifest.read_text()) if args.firmware_manifest else None
    deadline=time.monotonic()+args.timeout
    try:
        while time.monotonic()<deadline:
            try:
                if not link.interface and not link.connect():time.sleep(1);continue
                folder=collect(link,args.output,args.reboot_download,expected)
                if folder:
                    link.close()
                    if (folder/'download-requested.json').exists():
                        until=time.monotonic()+45
                        while time.monotonic()<until:
                            devices=[x for x in link.paths('{A5DCBF10-6530-11D2-901F-00C04FB951ED}')
                                     if 'vid_04e8&pid_685d' in x.lower()]
                            if len(devices)==1:
                                durable(folder/'download-confirmed.json',b'{"samsung_download_interface_present":true}\n')
                                break
                            if len(devices)>1: raise RuntimeError('Multiple Samsung download devices; no target chosen')
                            time.sleep(1)
                        else:
                            print('Log saved; download-mode enumeration not confirmed within45 seconds',flush=True)
                    print(folder,flush=True);return
            except OSError as e:
                link.close();print(f'USB unavailable: {e}',flush=True)
            time.sleep(1)
        raise SystemExit('Timed out without a complete saved snapshot; no blind reset requested')
    finally: link.close()


if __name__=='__main__': main()
