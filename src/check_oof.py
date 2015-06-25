import datetime
import os
import sys
from okean import cookbook as cb

p=os.path.dirname(os.path.realpath(__file__))
cmds={'A':'run_a.py', 'F':'run_f.py'}

def restart(FA):
  for i in FA:
    c=cmds[i]
    res=cb.run0('ps -e | grep '+c)
    if not res:
      logname=os.path.join(p,'log',c+'.log_'+datetime.datetime.now().strftime('%Y%m%d'))
      os.system(os.path.join(p,c)+' >> '+logname+' 2>&1&')

if __name__=='__main__':
  if len(sys.argv)>1: FA=sys.argv[1]
  else: FA='fa'
  restart(FA.upper())
