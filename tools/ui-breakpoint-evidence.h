/* M69: bounded terminal EL0 breakpoint registers, with no user-memory reads. */
static void
xcover5_ui_breakpoint_evidence(arm_saved_state_t *state, uint32_t esr)
{
    char name[32];
    proc_name(proc_selfpid(), name, sizeof(name));
    unsigned slot;
    if (__builtin_strcmp(name, "SpringBoard") == 0) slot = 0;
    else if (__builtin_strcmp(name, "backboardd") == 0) slot = 1;
    else return;
    static unsigned counts[2];
    if (os_atomic_inc_orig(&counts[slot], relaxed) >= 4) return;
    task_t task = current_task();
    printf("XCOVER5 M69 BRK pid=%d name=%s esr=%08x imm=%x\n",
        proc_selfpid(), name, esr, ISS_BRK_COMMENT(esr));
    printf("M69 PC=%016llx LR=%016llx SP=%016llx\n",
        (unsigned long long)get_saved_state_pc(state),
        (unsigned long long)get_saved_state_lr(state),
        (unsigned long long)get_saved_state_sp(state));
    printf("M69 MAIN=%016llx CACHE_SLIDE=%08x CPSR=%08x\n",
        task ? (unsigned long long)task->mach_header_vm_address : 0ULL,
        task ? task->task_shared_region_slide : ~0U, get_saved_state_cpsr(state));
    if (is_saved_state64(state)) {
        printf("M69 FP=%016llx\n", (unsigned long long)saved_state64(state)->fp);
        for (unsigned i = 0; i < 28; i += 2)
            printf("M69 X%u=%016llx X%u=%016llx\n", i,
                (unsigned long long)saved_state64(state)->x[i], i + 1,
                (unsigned long long)saved_state64(state)->x[i + 1]);
        printf("M69 X28=%016llx\n", (unsigned long long)saved_state64(state)->x[28]);
    }
}
