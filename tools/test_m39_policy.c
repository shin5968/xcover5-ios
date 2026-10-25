
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdbool.h>
#define ENOPOLICY 103
#define PROC_NULL NULL
#define user_addr_t uintptr_t
typedef bool boolean_t;
typedef int pid_t;
struct process {int pid,ppid,version,uid,bits;const char *p_comm;};
typedef struct process *proc_t;
typedef struct process *kauth_cred_t;
static struct process caller={1,0,1,0,1,"launchd"}, server={6,1,6,0,1,"m36-probe"}, child={7,6,7,0,1,"m36-probe"};
static proc_t initproc=&caller;
static int refs,creds,fault;
int proc_pid(proc_t p){return p->pid;}
int proc_ppid(proc_t p){return p->ppid;}
int proc_pidversion(proc_t p){return p->version;}
int proc_is64bit_data(proc_t p){return p->bits;}
proc_t proc_find(int pid){proc_t p=pid==1?&caller:pid==6?&server:pid==7?&child:NULL;if(p)refs++;return p;}
void proc_rele(proc_t p){assert(p);refs--;}
kauth_cred_t kauth_cred_proc_ref(proc_t p){creds++;return p;}
bool kauth_cred_issuser(kauth_cred_t p){return p->uid==0;}
void kauth_cred_unref(kauth_cred_t*p){creds--;}
int copyin(user_addr_t p,void*q,size_t n){if(!p||fault==1)return EFAULT;memcpy(q,(void*)p,n);return 0;}
int copyinstr(user_addr_t p,char*q,size_t n,size_t*l){if(!p||fault==2)return EFAULT;size_t z=strlen((char*)p)+1;if(z>n)return ENAMETOOLONG;memcpy(q,(void*)p,z);*l=z;return 0;}
int copyout(void*p,user_addr_t q,size_t n){if(!q||fault==3)return EFAULT;memcpy((void*)q,p,n);return 0;}
static int
xcover5_bootstrap_check(proc_t caller, user_addr_t address)
{
    struct {
        uint64_t result, pid, operation, filter_type, filter, flags, pidversion;
    } a;
    char operation[32], service[64];
    size_t length;
    proc_t client, parent;
    kauth_cred_t cred;
    boolean_t allowed;
    uint64_t decision = 0;
    int error;

    if (proc_pid(caller) != 1 || !proc_is64bit_data(caller)) {
        return ENOPOLICY;
    }
    error = copyin(address, &a, sizeof(a));
    if (error) { printf("XCOVER5 M36B: argument copy error=%d\n", error); return error; }
    if (a.pid == 0 || a.pid > INT_MAX || a.pidversion > UINT32_MAX ||
        a.flags != 0x40000000ULL) {
        printf("XCOVER5 M36B: ABI rejected pid=%llu filter=%llu flags=%llx version=%llu\n",
            (unsigned long long)a.pid, (unsigned long long)a.filter_type,
            (unsigned long long)a.flags, (unsigned long long)a.pidversion);
        return ENOPOLICY;
    }
    error = copyinstr(a.operation, operation, sizeof(operation), &length);
    if (error) { return error; }
    /* launchd wrapper API filters 2/3/12 become
     * internal 6/7/50. Cross-domain lookup uses internal filter 6. */
    boolean_t lookup = strcmp(operation, "mach-lookup") == 0;
    boolean_t cross = strcmp(operation, "mach-cross-domain-lookup") == 0;
    if (!lookup && !cross) { return ENOPOLICY; }
    if ((lookup && a.filter_type != 6 && a.filter_type != 7 && a.filter_type != 50) ||
        (cross && a.filter_type != 6)) {
        printf("XCOVER5 M36B: lookup rejected filter=%llu op=%s\n",
            (unsigned long long)a.filter_type, operation);
        return ENOPOLICY;
    }
    error = copyinstr(a.filter, service, sizeof(service), &length);
    if (error) { return error; }
    boolean_t exec_client = strcmp(service, "org.xcover5.m37.echo") == 0;
    boolean_t notify_client = strcmp(service, "com.apple.system.notification_center") == 0;
    boolean_t prefs_service = strcmp(service, "com.apple.cfprefsd.daemon") == 0 ||
        strcmp(service, "com.apple.cfprefsd.daemon.system") == 0;

    if (!prefs_service && !notify_client && !exec_client && strcmp(service, "org.xcover5.m36.echo") != 0) { return ENOPOLICY; }
    client = proc_find((pid_t)a.pid);
    if (client == PROC_NULL) { printf("XCOVER5 M36B: missing client pid=%llu\n", (unsigned long long)a.pid); return ESRCH; }
    boolean_t prefs_client = (prefs_service || notify_client) &&
        (strcmp(client->p_comm, "m39-probe") == 0 || strcmp(client->p_comm, "cfprefsd") == 0);
    cred = kauth_cred_proc_ref(client);
    allowed = kauth_cred_issuser(cred) &&
        (uint32_t)proc_pidversion(client) == a.pidversion &&
        (prefs_client || (!prefs_service && strcmp(client->p_comm, notify_client ? "m38-probe" : (exec_client ? "m37-client" : "m36-probe")) == 0));
    kauth_cred_unref(&cred);
    parent = proc_find(proc_ppid(client));
    allowed = allowed && parent != PROC_NULL && (notify_client ?
        (proc_pid(parent) == 1 && parent == initproc) :
        (proc_ppid(parent) == 1 && strcmp(parent->p_comm, exec_client ? "m37-server" : "m36-probe") == 0));
    if (prefs_client && parent != PROC_NULL) {
        cred = kauth_cred_proc_ref(client);
        allowed = kauth_cred_issuser(cred) && (uint32_t)proc_pidversion(client) == a.pidversion;
        kauth_cred_unref(&cred);
        boolean_t ancestry = parent == initproc && proc_pid(parent) == 1;
        if (!ancestry && strcmp(client->p_comm, "m39-probe") == 0 &&
            strcmp(parent->p_comm, "m39-probe") == 0 && proc_ppid(parent) == 1) {
            proc_t grandparent = proc_find(proc_ppid(parent));
            cred = kauth_cred_proc_ref(parent);
            ancestry = grandparent == initproc && kauth_cred_issuser(cred);
            kauth_cred_unref(&cred);
            if (grandparent != PROC_NULL) { proc_rele(grandparent); }
        }
        allowed = allowed && ancestry;
    }
    if (parent != PROC_NULL) { proc_rele(parent); }
    proc_rele(client);
    if (!allowed) {
        printf("XCOVER5 M36B: lookup identity rejected pid=%llu version=%llu\n",
            (unsigned long long)a.pid, (unsigned long long)a.pidversion);
        return EPERM;
    }
    error = copyout(&decision, a.result, sizeof(decision));
    if (!error) {
        printf("XCOVER5 M37: scoped lookup allowed pid=%llu filter=%llu op=%s\n", (unsigned long long)a.pid, (unsigned long long)a.filter_type, operation);
    }
    return error;
}

#define XCOVER5 1
#define __unused
#define MAC_MAX_POLICY_NAME 32
#define AUDIT_ARG(...) ((void)0)
typedef unsigned int u_int;
struct __mac_syscall_args {user_addr_t policy;int call;user_addr_t arg;};
struct ops {int (*mpo_policy_syscall)(proc_t,int,user_addr_t);};
struct mac_policy_conf {const char *mpc_name;struct ops *mpc_ops;};
struct {unsigned staticmax,maxindex;struct {struct mac_policy_conf*mpc;} entries[3];} mac_policy_list;
static int busy_count,precheck,policy_calls,policy_result;
int mac_proc_check_mac_syscall(proc_t p,const char*t,int c){return precheck;}
int mac_policy_list_conditional_busy(void){busy_count++;return 1;}
void mac_policy_list_unbusy(void){busy_count--;}
int existing_policy(proc_t p,int c,user_addr_t a){policy_calls++;return policy_result;}
int
__mac_syscall(proc_t p, struct __mac_syscall_args *uap, int *retv __unused)
{
	struct mac_policy_conf *mpc;
	char target[MAC_MAX_POLICY_NAME];
	int error;
	u_int i;
	size_t ulen;

	error = copyinstr(uap->policy, target, sizeof(target), &ulen);
	if (error) {
		return error;
	}
	AUDIT_ARG(value32, uap->call);
	AUDIT_ARG(mac_string, target);

	error = mac_proc_check_mac_syscall(p, target, uap->call);
	if (error) {
		return error;
	}

	error = ENOPOLICY;

	for (i = 0; i < mac_policy_list.staticmax; i++) {
		mpc = mac_policy_list.entries[i].mpc;
		if (mpc == NULL) {
			continue;
		}

		if (strcmp(mpc->mpc_name, target) == 0 &&
		    mpc->mpc_ops->mpo_policy_syscall != NULL) {
			error = mpc->mpc_ops->mpo_policy_syscall(p,
			    uap->call, uap->arg);
			goto done;
		}
	}
	if (mac_policy_list_conditional_busy() != 0) {
		for (; i <= mac_policy_list.maxindex; i++) {
			mpc = mac_policy_list.entries[i].mpc;
			if (mpc == NULL) {
				continue;
			}

			if (strcmp(mpc->mpc_name, target) == 0 &&
			    mpc->mpc_ops->mpo_policy_syscall != NULL) {
				error = mpc->mpc_ops->mpo_policy_syscall(p,
				    uap->call, uap->arg);
				mac_policy_list_unbusy();
				goto done;
			}
		}
		mac_policy_list_unbusy();
	}

#if defined(XCOVER5)
    if (uap->call == 2 && strcmp(target, "Sandbox") == 0) {
        error = xcover5_bootstrap_check(p, uap->arg);
    }
#endif

done:
	return error;
}

int main(void){
 uint64_t result=99,a[7]={(uintptr_t)&result,7,(uintptr_t)"mach-lookup",7,(uintptr_t)"org.xcover5.m36.echo",0x40000000,7};
 #define CHECK(e) do{assert(xcover5_bootstrap_check(&caller,(uintptr_t)a)==(e));assert(refs==0&&creds==0);}while(0)
 CHECK(0);assert(result==0);result=99;
 a[4]=(uintptr_t)"org.xcover5.m37.echo";CHECK(EPERM);
 child.p_comm="m37-client";CHECK(EPERM);server.p_comm="m37-server";CHECK(0);
 a[4]=(uintptr_t)"org.xcover5.m36.echo";CHECK(EPERM);
 child.p_comm="m36-probe";server.p_comm="m36-probe";result=99;
 caller.pid=2;CHECK(ENOPOLICY);caller.pid=1;
 caller.bits=0;CHECK(ENOPOLICY);caller.bits=1;
 a[1]=0;CHECK(ENOPOLICY);a[1]=UINT64_MAX;CHECK(ENOPOLICY);a[1]=8;CHECK(ESRCH);a[1]=7;
 a[6]=8;CHECK(EPERM);a[6]=7;
 a[3]=6;CHECK(0);a[3]=50;CHECK(0);a[3]=5;CHECK(ENOPOLICY);a[3]=7;
 a[2]=(uintptr_t)"mach-cross-domain-lookup";CHECK(ENOPOLICY);a[3]=6;CHECK(0);a[3]=50;CHECK(ENOPOLICY);a[3]=7;a[2]=(uintptr_t)"mach-lookup";result=99;
 a[5]=0;CHECK(ENOPOLICY);a[5]=0x40000000;
 a[2]=(uintptr_t)"file-read";CHECK(ENOPOLICY);a[2]=(uintptr_t)"mach-lookup";
 a[4]=(uintptr_t)"org.xcover5.m36.echox";CHECK(ENOPOLICY);a[4]=(uintptr_t)"org.xcover5.m36.echo";
 child.uid=501;CHECK(EPERM);child.uid=0;
 child.p_comm="other";CHECK(EPERM);child.p_comm="m36-probe";
 child.ppid=8;CHECK(EPERM);child.ppid=6;
 server.ppid=2;CHECK(EPERM);server.ppid=1;
 server.p_comm="other";CHECK(EPERM);server.p_comm="m36-probe";
 for(fault=1;fault<=3;fault++){CHECK(EFAULT);}fault=0;
 assert(result==99);puts("scoped helper: positive, identity, operation, service, ABI and copy fault tests PASS");

 struct __mac_syscall_args args={(uintptr_t)"Sandbox",2,(uintptr_t)a};
 int retv=0;struct ops ops={existing_policy};struct mac_policy_conf policy={"Sandbox",&ops};
 #define DISPATCH(want) do {assert(__mac_syscall(&caller,&args,&retv)==(want));assert(busy_count==0&&refs==0&&creds==0);}while(0)
 mac_policy_list.staticmax=1;mac_policy_list.maxindex=1;
 DISPATCH(0);
 args.call=3;DISPATCH(ENOPOLICY);args.call=2;
 args.policy=(uintptr_t)"Other";DISPATCH(ENOPOLICY);args.policy=(uintptr_t)"Sandbox";
 precheck=EPERM;DISPATCH(EPERM);precheck=0;
 mac_policy_list.entries[0].mpc=&policy;policy_result=ENOPOLICY;DISPATCH(ENOPOLICY);assert(policy_calls==1);
 policy_result=EPERM;DISPATCH(EPERM);policy_result=0;DISPATCH(0);
 mac_policy_list.entries[0].mpc=NULL;mac_policy_list.entries[1].mpc=&policy;
 policy_result=ENOPOLICY;DISPATCH(ENOPOLICY);policy_result=EPERM;DISPATCH(EPERM);policy_result=0;DISPATCH(0);

 a[4]=(uintptr_t)"com.apple.system.notification_center";
 child.p_comm="m38-probe";child.ppid=1;CHECK(0);
 child.uid=501;CHECK(EPERM);child.uid=0;
 child.p_comm="notifyd";CHECK(EPERM);child.p_comm="m38-probe";
 child.ppid=6;CHECK(EPERM);child.ppid=1;
 a[4]=(uintptr_t)"com.apple.system.notification_centerx";CHECK(ENOPOLICY);
 a[4]=(uintptr_t)"com.apple.system.notification_center";
 initproc=&server;CHECK(EPERM);initproc=&caller;
 puts("M38 exact notify service/root client/live PID1 parent checks PASS");

 a[4]=(uintptr_t)"com.apple.cfprefsd.daemon";
 child.p_comm="m39-probe";CHECK(0);
 child.uid=501;CHECK(EPERM);child.uid=0;
 a[6]=8;CHECK(EPERM);a[6]=7;
 child.p_comm="other";CHECK(EPERM);child.p_comm="cfprefsd";CHECK(0);
 child.ppid=6;CHECK(EPERM);
 child.p_comm="m39-probe";server.p_comm="m39-probe";server.ppid=1;CHECK(0);
 server.uid=501;CHECK(EPERM);server.uid=0;
 initproc=&server;CHECK(EPERM);initproc=&caller;
 a[4]=(uintptr_t)"com.apple.cfprefsd.daemon.system";CHECK(0);
 a[4]=(uintptr_t)"com.apple.system.notification_center";CHECK(0);
 a[4]=(uintptr_t)"com.apple.cfprefsd.daemonX";CHECK(ENOPOLICY);
 puts("M39 service/UID/PIDversion/direct-init/fresh-reader ancestry tests PASS");
 assert(policy_calls==6);puts("actual dispatch: static/dynamic existing policy results and lock accounting PASS");
}

