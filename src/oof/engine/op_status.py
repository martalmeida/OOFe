import os
import time
from string import join as sjoin
from subprocess import Popen, PIPE

from okean import dateu, cookbook as cb
from okean.roms import roms_tools as rt

import op_tools as opt

class Model:
  def __init__(self,cf,date,FA):

    self.conf = cf
    self.date = date
    self.FA   = FA

    logfile=opt.nameof_log(date=date,FA=FA,cf=self.conf)
    if not os.path.isfile(logfile): logfile=False
    self.logfile=logfile

    self.load()

  def load(self):
    if not self.logfile:
      self.rout=False
      return False

    f=open(self.logfile)
    L=f.readlines()

    # tend and dt only written at the end of model run, so give some
    # invalid values:
    self.tend = -1
    self.tend_str = 'not ended'
    self.dt   = -1

    for i in range(len(L)-1):
      k=L[i].strip()
      val=L[i+1].strip()
      if k.find('[job/process id]')==0: self.pid      = val
      elif k.find('[queue/local]')==0:  self.job_type = val
#     elif k.find('[date]')==0:         self.date     = val
#     elif k.find('[FA]')==0:           self.FA       = val
      elif k.find('[tstart]')==0:       self.tstart,self.tstart_str  = int(val.split()[0]),sjoin(val.split()[1:])
      elif k.find('[tend]')==0:         self.tend,self.tend_str  = int(val.split()[0]),sjoin(val.split()[1:])
      elif k.find('[dt (min)]')==0:     self.dt=float(val)

    self.rout=opt.nameof('out','rout',date=self.date,FA=self.FA,cf=self.conf)

    return True


  def status(self,quiet=False):
    # reload:
    res=self.load()
    if not res:
      if not quiet: print 'log file not found for %s %s' % (self.date,self.FA)
      return 'unavailable'

    if self.dt==-1:
      # model didnt finnished
      # check its status
      if self.job_type=='local':
        res=cb.run0('ps '+str(self.pid))
        if len(res)==2:
          dt=time.time()-self.tstart
          msg='Model running for %.2f min' % (dt/60.)
          Status='running'
        else:
          Status='terminated'
          # check model stdout:
          if rt.is_roms_out_ok(self.rout):
             msg='Model terminated with SUCCESS (??)'
          else: msg='Model terminated with ERROR'

      else: # job type is queue
         c=Popen(('qstat',self.pid),stdout=PIPE,stderr=PIPE)
         o,e=c.communicate()
         if e:
           Status='terminated'
           if rt.is_roms_out_ok(self.rout):
             msg='Model terminated with SUCCESS (??)'
           else: msg='Model terminated with ERROR'

         else:
           queue_status=o.split()[-2]
           if queue_status=='R':
             Status='running'
           else:
             Status='submitted'

           dt=time.time()-self.tstart
           msg='Model is '+Status+' for %.2f min' % (dt/60.)

    else:
     Status='finnished'
     msg='Model finnished in %.2f min' % self.dt
     if rt.is_roms_out_ok(self.rout):
       msg+=' with SUCCESS'
     else: msg+=' with ERROR'

    if not quiet: print msg
    return Status


  def status_out(self,quiet=False):
    if not self.rout:
      if not quiet: print 'log file not found for %s %s' % (self.date,self.FA)
      return 0,0,0

    data=rt.roms_read_out(self.rout)
    time=data[0]

    # check model ended:
    # time may not have the full time since print to roms.out may not occur at every time step
    # get ntimes and dt to get the right time simulated:
    for l in open(self.rout).readlines():
      if l.find(' ntimes ')>-1: ntimes = int(l.split()[0])
      if l.find(' dt ')>-1:
        dt = float(l.split()[0])
        break

    expected=ntimes*dt/86400.

    if rt.is_roms_out_ok(self.rout):
      time1=time[0]+expected
    else:
      time1=time[-1]

    if not quiet: print 'Model runned from day %.2f to %.2f' % (time[0], time1)
    return time[0],time1, expected


  def progress(self,quiet=1):
    if not self.rout:
      if not quiet: print 'log file not found for %s %s' % (self.date,self.FA)
      return 0,0

    stat=self.status(quiet=1)
    if stat=='running':
       t0,t1,expected=self.status_out()
       out= (t1-t0)/expected*100., (time.time()-self.tstart)/60.
    elif stat=='terminated':
      out= 0, (self.tend-self.tstart)/60.
    elif stat=='finnished':
      out= 100, (self.tend-self.tstart)/60.
    elif status=='submitted':
       out= 0, (time.time()-self.tstart)/60.

    if not quiet: print 'progress= ', out[0], '% in ',out[1],' min'
    return out

def status(cf,date,FA,quiet=1):
  return Model(cf,date,FA).status(quiet=quiet)

def status_out(cf,date,FA,quiet=1):
  return Model(cf,date,FA).status_out(quiet=quiet)

def progress(cf,date,FA,quiet=1):
  return Model(cf,date,FA).progress(quiet=quiet)

def dates(cf,date,FA):
  ob=Model(cf,date,FA)
  if not ob.logfile: print 'not available'
  else: print 'model runned from %s to %s' % (ob.tstart_str,ob.tend_str)

def last_week(cf):
  y.m,d=dateu.parse_date(dateu.currday())
  # show info about last week status... or something like that TODO


if __name__ == '__main__':
  from sys import argv
  if len(argv)<5:
    print 'usage: '
    print 'op_stat.py <conf> <date> <FA> <option>'
    print '<option>: status, status_out, progress, dates'

  else:
    cf     = argv[1]
    date   = argv[2]
    FA     = argv[3]
    action = argv[4]

    if action == 'status':
      status(cf,date,FA,quiet=0)
    if action == 'status_out':
      status_out(cf,date,FA,quiet=0)
    elif action == 'progress':
      progress(cf,date,FA,quiet=0)
    elif action == 'dates':
      dates(cf,date,FA)


