
# user's conf --------------------------------------------------------
grdFile  = 'PATH TO FILE *** EDIT ***'
iniFile  = 'PATH TO FILE *** EDIT ***'
iniDate  = 'YYYYMMDD     *** EDIT ***'
clmFile  = False
fltFile  = False
staFile  = False
frcFile  = 'PATH TO FILE *** EDIT ***'

runFileA = 'PATH TO FILE *** EDIT ***'
runFileF = 'PATH TO FILE *** EDIT ***'

atmPath  = 'PATH TO FILE *** EDIT ***'

# end of user's conf ---------------------------------------------------

import os
import sys
import glob
import shutil
import dateutil.parser

def update_executable():
  '''set sys.executable in python scripts
  ie, modules starting by #!
  '''

  files = []
  for (dirpath, dirnames, filenames) in os.walk(os.curdir):
    for f in filenames:
      ext=os.path.splitext(f)[-1]
      if ext=='.py':
         f=os.path.join(dirpath,f)
         lines=open(f).readlines()
         line=lines[0].strip()
         if line.startswith('#!'):
           print line
           exc=line.split('#!')[1].split()[0]
           if exc!=sys.executable:
             # edit file
             lines[0]=line.replace(exc,sys.executable)
             print 'updating sys.executable in file %s'%f
             open(f,'w').writelines(lines)


def start(quiet=0,**kargs):

  base='oof'
  conf   = 'oof.conf'
  dir0=os.path.realpath(os.curdir)
  os.chdir(base)
  sys.path.append('.')
  #cf=os.path.join(base,conf)
  cf=conf

  # create folders
  print ':: creating folders'
  from engine import op_tools as ot
  ot.mk_paths(cf)

  # link input file grd:
  grd=ot.nameof('in','grd',cf=cf)
  print ':: linking grd: %s' % grdFile
  if os.path.isfile(grd):  print '  already exists'
  else: os.symlink(grdFile,grd)

  # link input file clm:
  if clmFile:
    clm=ot.nameof('in','clm',cf=cf)
    print ':: linking clm: %s' % clmFile
    if os.path.isfile(clm):  print '  already exists'
    else: os.symlink(clmFile,clm)

  # link input file rst:
  rstDate=dateutil.parser.parse(iniDate)-dateutil.parser.datetime.timedelta(days=1)
  rst=ot.nameof('out','rst',date=rstDate,FA='a',cf=cf)
  print ':: linking ini: %s' % iniFile
  if os.path.isfile(rst):  print '  already exists'
  else: os.symlink(iniFile,rst)

  # link run files:
  runLnkA=ot.nameof_run(cf,FA='a')
  runLnkF=ot.nameof_run(cf,FA='f')

  runLnkA_path=runLnkA[0]
  runLnkF_path=runLnkF[0]
  runLnkA_file=runLnkA[-1].split()[-1]
  runLnkF_file=runLnkF[-1].split()[-1]
  runLnkA=os.path.join(runLnkA_path,runLnkA_file)
  runLnkF=os.path.join(runLnkF_path,runLnkF_file)

  print ':: linking run file: %s' % runLnkA
  if os.path.isfile(runLnkA):  print '  already exists'
  else: os.symlink(runFileA,runLnkA)

  print ':: linking run file: %s' % runLnkF
  if os.path.isfile(runLnkF):  print '  already exists'
  else: os.symlink(runFileF,runLnkF)


  # link input flt:
  if fltFile:
    flt=ot.nameof('in','flt',date='any',FA='any',cf=cf)
    print ':: linking flt: %s' % fltFile
    if os.path.isfile(flt):  print '  already exists'
    else: os.symlink(fltFile,flt)


  # link input sta:
  if staFile:
    sta=ot.nameof('in','sta',date='any',FA='any',cf=cf)
    print ':: linking sta: %s' % staFile
    if os.path.isfile(sta):  print '  already exists'
    else: os.symlink(staFile,sta)


  # link input frc:
  if frcFile:
    frc=ot.nameof('in','frc',date='any',FA='any',cf=cf)
    print ':: linking frc: %s' % frcFile
    if os.path.isfile(frc):  print '  already exists'
    else: os.symlink(frcFile,frc)


  # link atm data  path:
  if atmPath:
    print ':: linking atm data path: %s' %  atmPath
    atm_path = ot.pathof(cf,'external','atm')
    if os.path.islink(atm_path): print '  already exists'
    else:
      if os.path.isdir(atm_path): os.rmdir(atm_path)
      os.symlink(atmPath,atm_path)

  # move tmp files: *in  to rin0 folder:
  rinPath=ot.pathof(cf,'inputs','rin0')
  #tmpFilesFolder=os.path.join(base,'tmp_files')
  tmpFilesFolder='tmp_files'
  fin=glob.glob(os.path.join(tmpFilesFolder,'*.in'))
  for i in fin:
    iname=os.path.join(rinPath,os.path.basename(i))
    print ':: moving tmp file: %s' % iname
    if os.path.isfile(iname):  print '  already exists'
    else:  shutil.move(i,iname)

  # remove tmp folder:
  print ':: removing tmp folder: %s' % tmpFilesFolder
  if os.path.isdir(tmpFilesFolder):
    shutil.rmtree(tmpFilesFolder)
  else:
    print '  already done'

  # updating executable in all scripts:
  print ':: updating executable'
  os.chdir(dir0)
  update_executable()


if __name__=='__main__':
  start()


