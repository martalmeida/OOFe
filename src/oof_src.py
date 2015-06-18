'''
Create sources of current oof implementation

all files needed will be copied... then run setup.py to install in another place

mma 10-jul-2010
'''

import time
import glob
import shutil
from os.path import join
import os

def gen_src(base,dest,test=True):

  print 'creating folder %s' % dest
  if not test: os.mkdir(dest)
  files=glob.glob(join(base,'*.py'))
  for f in files:
    print 'coping %s to %s' % (f,dest)
    if not test: shutil.copy2(f,dest)


  print 'creating folder %s' % join(dest,'log')
  if not test: os.mkdir(join(dest,'log'))
  print 'creating folder %s' % join(dest,'oof')
  if not test: os.mkdir(join(dest,'oof'))
  print 'creating folder %s' % join(dest,'engine')
  if not test: os.mkdir(join(dest,'oof','engine'))
  print 'creating folder %s' % join(dest,'tmp_files')
  if not test: os.mkdir(join(dest,'oof','tmp_files'))
  print 'creating folder %s' % join(dest,'aux')
  if not test: os.mkdir(join(dest,'oof','aux'))
  print 'creating folder %s' % join(dest,'aux','qsub')
  if not test: os.mkdir(join(dest,'oof','aux','qsub'))
  print 'creating folder %s' % join(dest,'aux','apptools')
  if not test: os.mkdir(join(dest,'oof','aux','apptools'))
  print 'creating folder %s' % join(dest,'aux','tmp')
  if not test: os.mkdir(join(dest,'oof','aux','tmp'))


  files=glob.glob(join(base,'oof','*.conf'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof'))
    if not test: shutil.copy2(f,join(dest,'oof'))

  files=glob.glob(join(base,'oof','engine','*.py'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','engine'))
    if not test: shutil.copy2(f,join(dest,'oof','engine'))

  files=glob.glob(join(base,'oof','inputs','roms_in','roms_n*.in'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','tmp_files'))
    if not test: shutil.copy2(f,join(dest,'oof','tmp_files'))
  files=glob.glob(join(base,'oof','inputs','roms_in','ocean_?_n0.in'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','tmp_files'))
    if not test: shutil.copy2(f,join(dest,'oof','tmp_files'))

  files=glob.glob(join(base,'oof','aux','qsub','model.*'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','aux','qsub'))
    if not test: shutil.copy2(f,join(dest,'oof','aux','qsub'))

  files=glob.glob(join(base,'oof','aux','apptools','*.py'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','aux','apptools'))
    if not test: shutil.copy2(f,join(dest,'oof','aux','apptools'))

  files=glob.glob(join(base,'oof','aux','tmp','*'))
  for f in files:
    print 'coping %s to %s' % (f,join(dest,'oof','aux','tmp'))
    if not test: shutil.copy2(f,join(dest,'oof','aux','tmp'))


def setup_unset(f,test=True):
  '''
  deletes configuration, in file setup.py
  '''

  print 'unsetting current setup'
  if test:
    # use original file as a test
    psrc=os.path.dirname(os.path.dirname(f))
    name=os.path.basename(f)
    f=os.path.join(psrc,name)

  lines=open(f).readlines()

  i0=0
  while not lines[i0].startswith('# user'):
    i0+=1

  for i in range(i0+1,len(lines)):
    if not lines[i].strip(): continue
    if lines[i].startswith('# end of'): break

    tmp=lines[i].split('=')
    if tmp[1].strip() in ('True','False'):
      s=tmp[1].strip()
    elif 'Date' in tmp[0]:
      s="'YYYYMMDD     *** EDIT ***'"
    else:
      s="'PATH TO FILE *** EDIT ***'"

    lines[i]='%-8s = %s\n'%(tmp[0].strip(),s)

  if not test:
    open(f,'w').writelines(lines)


def to_tar_gz(source_dir, destination):
  """
  param source_dir: Source directory name.
  param destination: Destination filename.
  (TAR-GZ-Archive *.tar.gz)
  """
  import tarfile
  t = tarfile.open(name = destination, mode = 'w:gz')
  t.add(source_dir, os.path.basename(source_dir))
  t.close()


if __name__=='__main__':
  base='.'
  dest='oof_src_'+time.strftime('%Y%m%d_%H%M%S')
  import sys
  try:
    test=int(sys.argv[1])
  except: test=1

  if test: print '*** TEST ***'
  gen_src(base,dest,test)

  setup_unset(os.path.join(dest,'setup.py'),test)

  if not test:
    to_tar_gz(dest,dest+'.tar.gz')
    shutil.rmtree(dest)
  print '** created %s **' % (dest+'.tar.gz')


