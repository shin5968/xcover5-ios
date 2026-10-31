/* HackiOS portable APFS/ramfs registration; HFS remains the boot filesystem. */
#include <sys/systm.h>
#include <sys/mount_internal.h>
#include <sys/vnode_internal.h>
extern struct vfsops apfs_vfsops,ramfs_vfsops;
extern const struct vnodeopv_desc apfs_vnodeop_opv_desc,ramfs_vnodeop_opv_desc;
void xcover_filesystems_register(void);
void xcover_filesystems_register(void) {
 static vfstable_t handles[2];
 struct vfsops *ops[]={&apfs_vfsops,&ramfs_vfsops};
 const struct vnodeopv_desc *descs[]={&apfs_vnodeop_opv_desc,&ramfs_vnodeop_opv_desc};
 const char *names[]={"apfs","ramfs"};
 for(unsigned i=0;i<2;i++){
  struct vnodeopv_desc *list[]={(struct vnodeopv_desc *)descs[i]};
  struct vfs_fsentry entry={.vfe_vfsops=ops[i],.vfe_vopcnt=1,.vfe_opvdescs=list,
   .vfe_flags=VFS_TBLNOTYPENUM|VFS_TBL64BITREADY|VFS_TBLLOCALVOL|VFS_TBLGENERICMNTARGS|
   VFS_TBLTHREADSAFE|VFS_TBLNATIVEXATTR|
   (i==0?VFS_TBLREADDIR_EXTENDED:0)|
   VFS_TBLVNOP_PAGEINV2|VFS_TBLVNOP_PAGEOUTV2};
  strlcpy(entry.vfe_fsname,names[i],sizeof(entry.vfe_fsname));
  int rc=vfs_fsadd(&entry,&handles[i]);
  printf("XCOVER5 M72 FILESYSTEM name=%s register=%d; boot=hfs\n",names[i],rc);
  printf("XCOVER5 M75 READDIR name=%s extended=%u register=%d\n",names[i],i==0,rc);
 }
}
