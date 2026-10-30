/* Actual instrumented XNU permission function; checked against applied source. */
static int
exec_check_permissions(struct image_params *imgp)
{
	struct vnode *vp = imgp->ip_vp;
	struct vnode_attr *vap = imgp->ip_vattr;
	proc_t p = vfs_context_proc(imgp->ip_vfs_context);
	int error;
	kauth_action_t action;

	/* Only allow execution of regular files */
	if (!vnode_isreg(vp)) {
		XC58_STAGE(imgp,"not_regular",EACCES);
		return EACCES;
	}

	/* Get the file attributes that we will be using here and elsewhere */
	VATTR_INIT(vap);
	VATTR_WANTED(vap, va_uid);
	VATTR_WANTED(vap, va_gid);
	VATTR_WANTED(vap, va_mode);
	VATTR_WANTED(vap, va_fsid);
	VATTR_WANTED(vap, va_fsid64);
	VATTR_WANTED(vap, va_fileid);
	VATTR_WANTED(vap, va_data_size);
	if ((error = vnode_getattr(vp, vap, imgp->ip_vfs_context)) != 0) {
		XC58_STAGE(imgp,"getattr",error);
		return error;
	}

	XC58_ATTRS(imgp);
	/*
	 * Ensure that at least one execute bit is on - otherwise root
	 * will always succeed, and we don't want to happen unless the
	 * file really is executable.
	 */
	if (!vfs_authopaque(vnode_mount(vp)) && ((vap->va_mode & (S_IXUSR | S_IXGRP | S_IXOTH)) == 0)) {
		XC58_STAGE(imgp,"no_execute_bits",EACCES);
		return EACCES;
	}

	/* Disallow zero length files */
	if (vap->va_data_size == 0) {
		XC58_STAGE(imgp,"zero_size",ENOEXEC);
		return ENOEXEC;
	}

	imgp->ip_arch_offset = (user_size_t)0;
#if __LP64__
	imgp->ip_arch_size = vap->va_data_size;
#else
	if (vap->va_data_size > UINT32_MAX) {
		return ENOEXEC;
	}
	imgp->ip_arch_size = (user_size_t)vap->va_data_size;
#endif

	/* Disable setuid-ness for traced programs or if MNT_NOSUID */
	if ((vp->v_mount->mnt_flag & MNT_NOSUID) || (p->p_lflag & P_LTRACED)) {
		vap->va_mode &= ~(VSUID | VSGID);
	}

	/*
	 * Disable _POSIX_SPAWN_ALLOW_DATA_EXEC and _POSIX_SPAWN_DISABLE_ASLR
	 * flags for setuid/setgid binaries.
	 */
	if (vap->va_mode & (VSUID | VSGID)) {
		imgp->ip_flags &= ~(IMGPF_ALLOW_DATA_EXEC | IMGPF_DISABLE_ASLR);
	}

#if CONFIG_MACF
	error = mac_vnode_check_exec(imgp->ip_vfs_context, vp, imgp);
	XC58_STAGE(imgp,"mac_exec",error);
	if (error) {
		return error;
	}
#endif

	/* Check for execute permission */
	action = KAUTH_VNODE_EXECUTE;
	/* Traced images must also be readable */
	if (p->p_lflag & P_LTRACED) {
		action |= KAUTH_VNODE_READ_DATA;
	}
	if ((error = vnode_authorize(vp, NULL, action, imgp->ip_vfs_context)) != 0) {
		XC58_STAGE(imgp,"vnode_authorize",error);
		return error;
	}

	XC58_STAGE(imgp,"vnode_authorize",0);
#if 0
	/* Don't let it run if anyone had it open for writing */
	vnode_lock(vp);
	if (vp->v_writecount) {
		panic("going to return ETXTBSY %x", vp);
		vnode_unlock(vp);
		return ETXTBSY;
	}
	vnode_unlock(vp);
#endif

	/* XXX May want to indicate to underlying FS that vnode is open */

	return error;
}
