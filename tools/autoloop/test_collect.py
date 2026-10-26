from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib
import collect as c

class Link:
    def __init__(self,body=b'test log\n'):
        self.body=body;self.calls=[];self.short=False;self.change=False
        self.meta=c.META.pack(c.MAGIC,123,1,1,len(body),zlib.crc32(body),0,0x8e00)
    def transfer(self,request,offset=0,data=None,length=0):
        self.calls.append(request)
        if request==0x40:
            if self.change and self.calls.count(0x40)>1:return self.meta[:-1]+b'\x01'
            return self.meta
        if request==0x41:return self.body[offset:offset+length-(1 if self.short else 0)]
        if request==0x42:assert data==self.meta
        return b''

class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_save_ack_reset(self):
        link=Link(bytes(range(256))*3);folder=c.collect(link,self.root,True)
        self.assertEqual((folder/'console.bin').read_bytes(),link.body)
        self.assertEqual(link.calls[-2:],[0x42,0x43]);self.assertTrue((folder/'COMPLETE').exists())
    def test_no_reset_default(self):
        link=Link();c.collect(link,self.root);self.assertIn(0x42,link.calls);self.assertNotIn(0x43,link.calls)
    def test_bad_paths_never_ack(self):
        for problem in ['short','change','crc','overflow','pending']:
            with self.subTest(problem=problem):
                link=Link();link.short=problem=='short';link.change=problem=='change'
                fields=list(c.META.unpack(link.meta))
                if problem=='crc':fields[5]^=1
                if problem=='overflow':fields[6]=1
                if problem=='pending':fields[3]=0
                link.meta=c.META.pack(*fields)
                if problem=='pending':self.assertIsNone(c.collect(link,self.root,True))
                else:
                    with self.assertRaises((ValueError,IOError)):c.collect(link,self.root,True)
                self.assertNotIn(0x42,link.calls);self.assertNotIn(0x43,link.calls)
    def test_disk_failure_never_ack(self):
        link=Link()
        with patch.object(c,'durable',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):c.collect(link,self.root,True)
        self.assertNotIn(0x42,link.calls);self.assertNotIn(0x43,link.calls)
    def test_no_overwrite(self):
        link=Link()
        with patch.object(c.time,'strftime',return_value='fixed'):
            c.collect(link,self.root)
            with self.assertRaises(FileExistsError):c.collect(link,self.root)
    def test_bad_metadata(self):
        for raw in [b'',bytes(40),c.META.pack(c.MAGIC,123,1,1,c.CAP+1,0,0,0)]:
            with self.assertRaises(ValueError):c.parse_meta(raw)

if __name__=='__main__':unittest.main()
